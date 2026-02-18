"""Auth schemas."""

from pydantic import BaseModel


class AdminLogin(BaseModel):
    username: str
    password: str


class JudgeLogin(BaseModel):
    access_code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminRead(BaseModel):
    User_ID: str
    Username: str
    Role: str

    model_config = {"from_attributes": True}
