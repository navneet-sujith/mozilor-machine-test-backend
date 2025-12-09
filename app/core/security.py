from datetime import datetime, timedelta
from typing import Optional, Union, Any
import hashlib

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

class SecurityService:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @staticmethod
    def _hash_password_pre(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        # Try verifying with pre-hashing (new way)
        if cls.pwd_context.verify(cls._hash_password_pre(plain_password), hashed_password):
            return True
        
        # Fallback for legacy passwords (not pre-hashed)
        # Only try if length is safe to avoid ValueError
        if len(plain_password.encode()) <= 72:
            return cls.pwd_context.verify(plain_password, hashed_password)
            
        return False

    @classmethod
    def get_password_hash(cls, password: str) -> str:
        return cls.pwd_context.hash(cls._hash_password_pre(password))

    @staticmethod
    def create_access_token(subject: Union[str, int], expires_delta: Optional[timedelta] = None) -> str:
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(subject: Union[str, int]) -> str:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
