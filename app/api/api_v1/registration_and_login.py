from typing import Generator, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token
from app.controllers.auth_controller import AuthController
from app.core.security import SecurityService
from app.api.deps import get_db
from app.core.rate_limiter import limiter
from fastapi import Request
from jose import jwt, JWTError
from app.core.config import settings
from pydantic import BaseModel

router = APIRouter()

@router.post("/register", response_model=UserResponse)
@limiter.limit("5/minute")
def register(request: Request, user: UserCreate, db: Session = Depends(get_db)) -> Any:
    auth_controller = AuthController(db)
    return auth_controller.create_user(user=user)

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, user_in: UserLogin, db: Session = Depends(get_db)) -> Any:
    auth_controller = AuthController(db)
    user = auth_controller.authenticate_user(user=user_in)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = SecurityService.create_access_token(subject=user.id)
    refresh_token = SecurityService.create_refresh_token(subject=user.id)
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=Token)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)) -> Any:
    """
    Refresh access token using a valid refresh token.
    """
    try:
        payload = jwt.decode(request.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    
    access_token = SecurityService.create_access_token(subject=user_id)
    # Rotate refresh token? Plan didn't specify, but often good practice. 
    # We will just return a new access token and same refresh token to keep it simple, 
    # OR better: return new refresh token too. Let's return new refresh token.
    new_refresh_token = SecurityService.create_refresh_token(subject=user_id)
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }
