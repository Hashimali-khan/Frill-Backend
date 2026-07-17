import re

from pydantic import BaseModel,field_validator, EmailStr

PK_PHONE_RE = re.compile(r"^(0|\+92)3[0-9]{9}$")

class SignupRequest(BaseModel):
    first_name:str
    last_name:str
    email:EmailStr
    phone:str
    password:str
    
    @field_validator("first_name", "last_name")
    @classmethod
    def min_len_2(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("Must be at least 2 characters")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def valid_pk_phone(cls, v: str) -> str:
        if not PK_PHONE_RE.match(v):
            raise ValueError("Enter a valid Pakistani phone number")
        return v

    @field_validator("password")
    @classmethod
    def min_len_8(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):

    email: EmailStr
    password: str


class UserResponse(BaseModel):

    id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    role: str

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None

    @field_validator("phone")
    @classmethod
    def valid_pk_phone_optional(cls, v: str | None) -> str | None:
        if v is not None and not PK_PHONE_RE.match(v):
            raise ValueError("Enter a valid Pakistani phone number")
        return v


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    access_token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def min_len_8(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v