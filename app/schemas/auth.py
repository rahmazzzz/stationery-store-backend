
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    user_id: str
    email: EmailStr | None = None
    requires_email_confirmation: bool = False


class CurrentUserResponse(BaseModel):
    user_id: str
    email: EmailStr | None = None