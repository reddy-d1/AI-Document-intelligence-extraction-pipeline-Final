from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.enums import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None


class UserLogin(BaseModel):
    email: str
    password: str = "password"


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole

    class Config:
        from_attributes = True
