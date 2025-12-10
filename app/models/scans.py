from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base_class import Base
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey

class Scans(Base):
    __tablename__ = "scans"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    alt_images = Column(Integer, nullable=False)
    non_alt_images = Column(Integer, nullable=False)
    total_images = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="scans")