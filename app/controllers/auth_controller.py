from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin
from app.core.security import SecurityService
import logging

logger = logging.getLogger(__name__)

class AuthController:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()

    def create_user(self, user: UserCreate):
        db_user = self.get_user_by_email(email=user.email)
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_password = SecurityService.get_password_hash(user.password)
        db_user = User(
            email=user.email,
            name=user.name,
            hashed_password=hashed_password
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def authenticate_user(self, user: UserLogin):
        db_user = self.get_user_by_email(email=user.email)
        if not db_user:
            return None
        if not SecurityService.verify_password(user.password, db_user.hashed_password):
            logger.warning(f"Failed login attempt for email: {user.email}")
            return None
        return db_user
