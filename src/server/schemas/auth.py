from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    user_id: str = Field(min_length=2, max_length=64)
    phone: str = Field(min_length=8, max_length=32)
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(pattern="^(customer|bank_officer|agent)$")


class LoginRequest(BaseModel):
    user_id: str
    password: str
    device_id: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

