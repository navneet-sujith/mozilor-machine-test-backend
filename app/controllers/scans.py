from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.scans import Scans
from app.schemas.scan_schemas import ScanResponse
import logging

logger = logging.getLogger(__name__)

class ScanController:
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_score(self, scan: Scans):
        if scan.total_images == 0:
            return 0
        return round(scan.alt_images / scan.total_images * 100)
    
    def get_scans(self, user_id: int, search: str = None):
        scans = self.db.query(Scans).filter(Scans.user_id == user_id)
        if search:
            scans = scans.filter(Scans.url.contains(search)) 
        scans = scans.order_by(Scans.id.desc()).limit(10).all()
        for scan in scans:
            scan.total_images = scan.alt_images + scan.non_alt_images
            scan.score = self.calculate_score(scan)
        return scans

    def get_scan(self, user_id: int, scan_id: int):
        scan = self.db.query(Scans).filter(Scans.id == scan_id, Scans.user_id == user_id).first()
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
        scan.total_images = scan.alt_images + scan.non_alt_images
        scan.score = self.calculate_score(scan)
        return scan
    