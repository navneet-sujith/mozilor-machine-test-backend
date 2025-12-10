import pytest
from unittest.mock import MagicMock
from app.services.scan_service import ScanService, TREAT_EMPTY_ALT_AS_PRESENT

def test_parse_images_basic():
    html = """
    <html>
        <body>
            <img src="valid.jpg" alt="A valid image">
            <img src="missing.jpg">
            <img src="empty.jpg" alt="">
            <div style="background-image: url('bg.jpg')"></div>
        </body>
    </html>
    """
    # Create service instance with mock DB
    service = ScanService(db=MagicMock())
    total, alt, non_alt = service.parse_images(html, "http://example.com")
    
    # Expected:
    # 1. valid.jpg -> has_alt=True
    # 2. missing.jpg -> has_alt=False
    # 3. empty.jpg -> has_alt=True (since constant is True by default)
    # 4. bg.jpg -> has_alt=False
    
    assert total == 4
    if TREAT_EMPTY_ALT_AS_PRESENT:
        assert alt == 2
        assert non_alt == 2
    else:
        assert alt == 1
        assert non_alt == 3

def test_parse_images_svg():
    html = """
    <html>
        <body>
            <svg role="img" aria-label="An SVG image"><image href="foo.png"/></svg>
            <svg><image href="bar.png"/></svg>
        </body>
    </html>
    """
    service = ScanService(db=MagicMock())
    total, alt, non_alt = service.parse_images(html, "http://example.com")
    
    # 1. svg with aria-label -> has_alt=True
    # 2. svg without -> has_alt=False
    
    assert total == 2
    assert alt == 1
    assert non_alt == 1

def test_parse_limits():
    # generate many images
    html = "".join(['<img src="img.jpg" alt="alt">' for _ in range(600)])
    service = ScanService(db=MagicMock())
    total, alt, non_alt = service.parse_images(html, "http://example.com")
    
    assert total == 500 # Capped at 500
    assert alt == 500
