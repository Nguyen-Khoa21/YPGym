from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.auth_schema import UserPublic


class UserProfileResponse(UserPublic):
    pass


class UserProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    current_password: str | None = Field(default=None, min_length=1, max_length=128)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)
    email: EmailStr | None = None

    @model_validator(mode="after")
    def validate_password_change(self) -> "UserProfileUpdateRequest":
        if self.new_password and not self.current_password:
            raise ValueError("Current password is required to change password.")
        return self
