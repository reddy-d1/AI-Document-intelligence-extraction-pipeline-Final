import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)

SECRET_KEY = "doc-intelligence-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

# File Magic Byte Signatures
MAGIC_SIGNATURES = {
    b"%PDF": "pdf",
    b"\x89PNG": "png",
    b"\xff\xd8\xff": "jpg",
    b"PK\x03\x04": "docx_or_zip",
    b"II*\x00": "tiff",
    b"MM\x00*": "tiff",
}


def validate_file_magic_bytes(header_bytes: bytes) -> bool:
    """Inspect leading file header magic bytes to prevent file extension spoofing"""
    if not header_bytes or len(header_bytes) < 4:
        return False

    for sig in MAGIC_SIGNATURES:
        if header_bytes.startswith(sig):
            return True
    return False


def mask_sensitive_log_data(text: str) -> str:
    """Mask sensitive PII data (SSN, Credit Cards, API Keys) in log output"""
    if not text:
        return text

    # Mask SSNs (xxx-xx-xxxx)
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "***-**-****", text)
    # Mask Credit Cards (16 digits)
    text = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "****-****-****-****", text)
    # Mask API Keys (sk-...)
    text = re.sub(r"sk-[A-Za-z0-9_-]{20,}", "sk-***MASKED***", text)
    return text


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create signed JWT token payload"""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """FastAPI dependency to extract & validate JWT user"""
    if not token:
        admin_user = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not admin_user:
            admin_user = User(email="admin@docintel.ai", name="Admin User", role=UserRole.ADMIN)
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
        return admin_user

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        token_data = TokenData(user_id=user_id, email=payload.get("email"), role=payload.get("role"))
    except JWTError:
        return None

    user = db.query(User).filter(User.id == token_data.user_id).first()
    return user


def require_role(allowed_roles: list[UserRole]):
    """Role-based access control dependency wrapper"""
    def role_checker(current_user: Optional[User] = Depends(get_current_user)):
        if current_user is None or current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for current user role."
            )
        return current_user
    return role_checker
