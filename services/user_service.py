import logging
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.system import CRUD
from app.modules.system.services.errors import DBErrorHandler

from ..models import TelegramUser, UserProfile
from ..schemas import TelegramUserCreate, UserProfileCreate


logger = logging.getLogger(__name__)


async def create_telegram_user(
    data: TelegramUserCreate,
    session: AsyncSession,
) -> tuple[TelegramUser, bool]:
    # Check if TelegramUser already exists to maintain idempotency.
    try:
        result = await session.execute(
            select(TelegramUser).where(TelegramUser.telegram_id == data.telegram_id)
        )
        telegram_user = result.scalars().first()
    except Exception as err:
        DBErrorHandler.handle(err=err, model=TelegramUser, action="reading")

    if telegram_user is not None:
        return telegram_user, False

    # Insert both user and profile atomically.
    try:
        # Use a nested transaction savepoint to handle potential concurrent inserts
        # on the unique telegram_id column without failing the entire transaction.
        async with session.begin_nested():
            telegram_user = TelegramUser(**data.model_dump())
            session.add(telegram_user)
            await session.flush()
    except IntegrityError:
        # A concurrent request may have inserted the user. Let's fetch it.
        try:
            result = await session.execute(
                select(TelegramUser).where(TelegramUser.telegram_id == data.telegram_id)
            )
            telegram_user = result.scalars().first()
        except Exception as err:
            DBErrorHandler.handle(err=err, model=TelegramUser, action="reading")

        if telegram_user is not None:
            return telegram_user, False
        raise
    except Exception as err:
        DBErrorHandler.handle(err=err, model=TelegramUser, action="creating")

    # Create the UserProfile
    try:
        user_profile = UserProfile(telegram_user_id=telegram_user.id)
        session.add(user_profile)
        await session.flush()
        await session.refresh(telegram_user)
        return telegram_user, True
    except Exception as err:
        DBErrorHandler.handle(err=err, model=UserProfile, action="creating")


async def bulk_create_telegram_users(
    data: list[TelegramUserCreate],
    session: AsyncSession,
) -> list[TelegramUser]:
    if not data:
        return []

    try:
        telegram_users = [TelegramUser(**item.model_dump()) for item in data]
        session.add_all(telegram_users)
        await session.flush()  # Populates id for each telegram_user

        user_profiles = [
            UserProfile(telegram_user_id=telegram_user.id)
            for telegram_user in telegram_users
        ]
        session.add_all(user_profiles)
        await session.flush()

        for telegram_user in telegram_users:
            await session.refresh(telegram_user)
        return telegram_users
    except Exception as err:
        DBErrorHandler.handle(err=err, model=TelegramUser, action="bulk creating")


async def login_telegram_user(
    telegram_id: int,
    session: AsyncSession,
) -> TelegramUser:
    try:
        result = await session.execute(
            select(TelegramUser).where(TelegramUser.telegram_id == telegram_id)
        )
        telegram_user = result.scalars().first()

        if telegram_user is None:
            raise HTTPException(
                status_code=404,
                detail=f"TelegramUser with telegram_id={telegram_id} not found.",
            )

        telegram_user.last_seen_at = datetime.utcnow()
        await session.flush()
        await session.refresh(telegram_user)
    except HTTPException:
        raise
    except Exception as err:
        DBErrorHandler.handle(err=err, model=TelegramUser, action="logging in")
    else:
        return telegram_user
