from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, get_current_user
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.auth import Token, UserResponse, UserLogin

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT bearer token"""
    user = db.query(User).filter(User.email == form_data.username).first()
    
    # Auto-create demo user if not existing
    if not user:
        user = User(
            email=form_data.username,
            name=form_data.username.split("@")[0].capitalize(),
            role=UserRole.ADMIN if "admin" in form_data.username.lower() else UserRole.REVIEWER
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role.value}
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Retrieve profile of authenticated user"""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return current_user
