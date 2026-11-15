from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .auth import CurrentUser, DB

router = APIRouter(prefix="/me")


class ProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    email_verified: bool
    display_name: str
    timezone_name: str
    cefr_level: str
    daily_goal: int


class ProfileEdit(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    timezone_name: str | None = Field(default=None, max_length=80)
    cefr_level: Literal["A2", "B1", "B2"] | None = None
    daily_goal: int | None = Field(default=None, ge=1, le=500, strict=True)

    @field_validator("timezone_name")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except (ValueError, ZoneInfoNotFoundError):
                raise ValueError("Unknown timezone") from None
        return value

    @model_validator(mode="after")
    def validate_nonnull_fields(self):
        for key in self.model_fields_set:
            if getattr(self, key) is None:
                raise ValueError(f"{key} cannot be null")
        return self


@router.get("")
def get_profile(user: CurrentUser) -> ProfileView:
    return ProfileView.model_validate(user)


@router.patch("")
def edit_profile(payload: ProfileEdit, user: CurrentUser, db: DB) -> ProfileView:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    result = ProfileView.model_validate(user)
    db.commit()
    return result
