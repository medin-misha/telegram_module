from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import database
from app.modules.system import CRUD

from .models import TelegramUser, UserProfile
from .schemas import (
    TelegramUserCreate,
    TelegramUserLogin,
    TelegramUserPatch,
    TelegramUserRead,
    UserProfileCreate,
    UserProfilePatch,
    UserProfileRead,
)
from .services import (
    bulk_create_telegram_users as bulk_create_telegram_users_service,
    create_telegram_user as create_telegram_user_service,
    login_telegram_user as login_telegram_user_service,
)


router = APIRouter(prefix="/telegram", tags=["telegram"])

SessionDep = Annotated[AsyncSession, Depends(database.get_session)]

# TelegramUser
@router.post("/login", response_model=TelegramUserRead)
async def login_telegram_user(
    data: TelegramUserLogin,
    session: SessionDep,
) -> TelegramUser:
    return await login_telegram_user_service(
        telegram_id=data.telegram_id,
        session=session,
    )


@router.post("/users", response_model=TelegramUserRead)
async def create_telegram_user(
    data: TelegramUserCreate,
    response: Response,
    session: SessionDep,
) -> TelegramUser:
    telegram_user, created = await create_telegram_user_service(data=data, session=session)
    response.status_code = (
        status.HTTP_201_CREATED if created else status.HTTP_200_OK
    )
    return telegram_user


@router.post(
    "/users/bulk",
    response_model=list[TelegramUserRead],
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_telegram_users(
    data: list[TelegramUserCreate],
    session: SessionDep,
) -> list[TelegramUser]:
    return await bulk_create_telegram_users_service(data=data, session=session)


@router.get("/users/{id}", response_model=TelegramUserRead)
async def get_telegram_user(
    id: int,
    session: SessionDep,
) -> TelegramUser:
    return await CRUD.get(model=TelegramUser, session=session, id=id)


@router.get("/users", response_model=list[TelegramUserRead])
async def list_telegram_users(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1)] = 10,
    search: str | None = None,
    field: str | None = None,
) -> list[TelegramUser]:
    return await CRUD.get(
        model=TelegramUser,
        session=session,
        page=page,
        limit=limit,
        search=search,
        field=field,
    )


@router.patch("/users/{id}", response_model=TelegramUserRead)
async def patch_telegram_user(
    id: int,
    data: TelegramUserPatch,
    session: SessionDep,
) -> TelegramUser:
    return await CRUD.patch(new_data=data, model=TelegramUser, session=session, id=id)


@router.delete("/users/{id}")
async def delete_telegram_user(
    id: int,
    session: SessionDep,
) -> dict[str, str]:
    result = await CRUD.delete(model=TelegramUser, session=session, id=id)
    return {"status": result}

# UserProfile
@router.post("/profile", response_model=UserProfileRead, status_code=status.HTTP_201_CREATED)
async def create_user_profile(
    data: UserProfileCreate,
    session: SessionDep,
) -> UserProfile:
    return await CRUD.create(data=data, model=UserProfile, session=session)


@router.get("/profile/{id}", response_model=UserProfileRead)
async def get_user_profile(
    id: int,
    session: SessionDep,
) -> UserProfile:
    return await CRUD.get(model=UserProfile, session=session, id=id)


@router.get("/profile", response_model=list[UserProfileRead])
async def list_user_profiles(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1)] = 10,
    search: str | None = None,
    field: str | None = None,
) -> list[UserProfile]:
    return await CRUD.get(
        model=UserProfile,
        session=session,
        page=page,
        limit=limit,
        search=search,
        field=field,
    )


@router.patch("/profile/{id}", response_model=UserProfileRead)
async def patch_user_profile(
    id: int,
    data: UserProfilePatch,
    session: SessionDep,
) -> UserProfile:
    return await CRUD.patch(new_data=data, model=UserProfile, session=session, id=id)


@router.delete("/profile/{id}")
async def delete_user_profile(
    id: int,
    session: SessionDep,
) -> dict[str, str]:
    result = await CRUD.delete(model=UserProfile, session=session, id=id)
    return {"status": result}
