from pydantic import BaseModel, ConfigDict


class GoogleLoginRequest(BaseModel):
    id_token: str  # the Google ID token obtained by the frontend Sign-In button


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None  # our user id, carried inside the app JWT


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
