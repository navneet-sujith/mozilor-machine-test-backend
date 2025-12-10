from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl

class ScanBase(BaseModel):
    url: HttpUrl

class ScanCreate(ScanBase):
    pass

class ScanResponse(ScanBase):
    id: int
    total_images: int = 0
    alt_images: int
    non_alt_images: int
    created_at: datetime
    score: int = 0

    
    class Config:
        from_attributes = True
