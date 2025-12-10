import socket
import ipaddress
import logging
import asyncio
from urllib.parse import urlparse
import aiohttp
from bs4 import BeautifulSoup
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.scans import Scans
from datetime import datetime

# Configuration Helpers
TREAT_EMPTY_ALT_AS_PRESENT = True
MAX_URL_LENGTH = 2048
MAX_IMAGE_ELEMENTS = 500
TIMEOUT_CONNECT = 5.0
TIMEOUT_READ = 10.0
TIMEOUT_TOTAL = 15.0
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

logger = logging.getLogger(__name__)

class ScanError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class ScanService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _is_private_ip(hostname: str) -> bool:
        try:
            # Resolve hostname to IP
            ip_list = socket.getaddrinfo(hostname, None)
            for item in ip_list:
                ip_addr = item[4][0]
                ip_obj = ipaddress.ip_address(ip_addr)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast:
                    return True
            return False
        except socket.gaierror:
            # If DNS fails, we treat it as unsafe/invalid
            return True

    def validate_url(self, url: str):
        if len(url) > MAX_URL_LENGTH:
            raise ScanError("URL too long")
        
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ScanError("Invalid URL scheme. Only http and https are allowed.")
        
        if not parsed.hostname:
            raise ScanError("Invalid URL: missing hostname.")
        
        if parsed.username or parsed.password:
            raise ScanError("URLs with credentials are not allowed.")

        if self._is_private_ip(parsed.hostname):
            raise ScanError("Target resolves to a private or disallowed IP address.", status_code=400)

    async def fetch_html(self, url: str) -> str:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        timeout = aiohttp.ClientTimeout(total=TIMEOUT_TOTAL, connect=TIMEOUT_CONNECT, sock_read=TIMEOUT_READ)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as client:
                for attempt in range(3): # Try 0, 1, 2
                    try:
                        async with client.get(url, headers=headers, ssl=True, allow_redirects=True) as response:
                            if response.status == 403:
                                # Cloudflare or generic WAF block
                                raise ScanError("Access forbidden by upstream server. The site may be blocking automated scans (Cloudflare/Bot protection).", status_code=424)
                            
                            if response.status >= 400:
                                raise ScanError(f"Upstream server returned {response.status}", status_code=502 if response.status >= 500 else 424)
                            
                            content_type = response.headers.get("Content-Type", "")
                            # Read content first to check for lazy checks if needed, but aiohttp reads on text()
                            # But we want to fail fast if not html?
                            # Replicating original logic:
                            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                                # Lax check needs content peek. aiohttp allows reading prefix?
                                # We'll just read text.
                                text = await response.text()
                                if not content_type and text.strip().startswith("<"):
                                     pass 
                                else:
                                    raise ScanError(f"Unsupported Media Type: {content_type}", status_code=415)
                            else:
                                text = await response.text()
                            
                            return text
                            
                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        if attempt == 2:
                            raise ScanError(f"Network error fetching URL: {str(e)}", status_code=502)
                        continue 
                    except ScanError:
                        raise
                    except Exception as e:
                            raise ScanError(f"Error fetching URL: {str(e)}", status_code=502)
        except ScanError:
            raise
        except Exception as e:
             raise ScanError(f"Unexpected error: {str(e)}", status_code=500)
        return ""

    def parse_images(self, html_content: str, base_url: str):
        soup = BeautifulSoup(html_content, "lxml")
        
        total_images = 0
        alt_images = 0
        non_alt_images = 0
        
        def process_element(has_alt: bool):
            nonlocal total_images, alt_images, non_alt_images
            if total_images >= MAX_IMAGE_ELEMENTS:
                return
            
            total_images += 1
            if has_alt:
                alt_images += 1
            else:
                non_alt_images += 1

        # 1. <img> tags
        for img in soup.find_all("img"):
            if total_images >= MAX_IMAGE_ELEMENTS: break
            
            alt = img.get("alt")
            has_alt = False
            if alt is not None:
                if alt.strip():
                    has_alt = True
                elif TREAT_EMPTY_ALT_AS_PRESENT:
                    has_alt = True
                else:
                    has_alt = False
            else:
                has_alt = False
                
            process_element(has_alt)

        # 2. Inline styles with background-image
        if total_images < MAX_IMAGE_ELEMENTS:
            for tag in soup.find_all(True, style=True):
                if total_images >= MAX_IMAGE_ELEMENTS: break
                style = tag["style"]
                if "background-image" in style and "url(" in style:
                    process_element(False)

        # 3. <svg> with <image> child
        if total_images < MAX_IMAGE_ELEMENTS:
            for svg in soup.find_all("svg"):
                if total_images >= MAX_IMAGE_ELEMENTS: break
                if svg.find("image") or svg.find("img"): 
                     has_alt = bool(svg.get("aria-label") or svg.get("title"))
                     process_element(has_alt)
            
        return total_images, alt_images, non_alt_images

    async def perform_scan(self, user_id: int, url_in: str) -> Scans:
        # 1. Validate
        self.validate_url(url_in)
        
        # 2. Fetch
        try:
            html_content = await self.fetch_html(url_in)
        except ScanError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

        # 3. Parse
        try:
            total, alt, non_alt = self.parse_images(html_content, url_in)
        except Exception as e:
            logger.error(f"Error parsing HTML for {url_in}: {e}")
            raise HTTPException(status_code=500, detail="Error parsing page content")

        # 4. Save
        scan = Scans(
            user_id=user_id,
            url=url_in,
            total_images=total,
            alt_images=alt,
            non_alt_images=non_alt,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(scan)
        try:
            await self.db.commit()
            await self.db.refresh(scan)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Database error saving scan: {e}")
            raise HTTPException(status_code=500, detail="Database error")
            
        return scan
