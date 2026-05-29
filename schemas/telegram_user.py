from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .user_profile import UserProfileRead

class TelegramUserBase(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    last_seen_at: datetime | None = None
    is_blocket_bot: bool = False
    language_code: str | None = None


class TelegramUserCreate(TelegramUserBase):
    pass


class TelegramUserLogin(BaseModel):
    telegram_id: int


class TelegramUserPatch(BaseModel):
    telegram_id: int | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    last_seen_at: datetime | None = None
    is_blocket_bot: bool | None = None
    language_code: str | None = None


class TelegramUserRead(TelegramUserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
    user_profile: UserProfileRead | None = None
