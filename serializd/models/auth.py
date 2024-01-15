from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    username: str
    token: str


class ValidateAuthTokenRequest(BaseModel):
    token: str


class ValidateAuthTokenResponse(BaseModel):
    isValid: bool
    username: str
