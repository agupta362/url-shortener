from pydantic import BaseModel, EmailStr
from typing import Optional

class UserRegister(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class URLCreate(BaseModel):
    original_url: str
    custom_code: Optional[str] = None

class TokenRefresh(BaseModel):
    refresh_token: str