from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserProfileBase(BaseModel):
    telegram_user_id: int
    phone: str | None = None
    email: str | None = None
    timezone: str | None = None
    full_name: str | None = None
    note: str | None = None


class UserProfileCreate(UserProfileBase):
    pass


class UserProfilePatch(BaseModel):
    telegram_user_id: int | None = None
    phone: str | None = None
    email: str | None = None
    timezone: str | None = None
    full_name: str | None = None
    note: str | None = None


class UserProfileRead(UserProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
