# Telegram Module Guide For AI Agents

## Purpose

`app.modules.telegram_module` is the reusable Telegram integration module for the FastAPI application.

Use it as the canonical place for Telegram bot user identity and profile data.
This module exists to:

- store Telegram-facing user identity in `TelegramUser`
- store collected profile data in `UserProfile`
- provide reusable create/login flows for Telegram users
- expose HTTP endpoints for authentication-adjacent Telegram user lifecycle operations

This module depends on `app.modules.system` and should reuse its shared persistence primitives instead of re-implementing them locally.

## Dependency On `system`

`telegram_module` is a feature module built on top of `system`.

Current dependencies:

- `Base` and `TimestampMixin` for ORM models
- `CRUD` for generic create/read/update/delete behavior
- `DBErrorHandler` for normalized database error handling

Preferred imports:

```python
from app.modules.system import Base, TimestampMixin, CRUD
from app.modules.system.services.errors import DBErrorHandler
```

Do not duplicate generic CRUD logic, timestamp mixins, or DB exception normalization inside this module unless the Telegram workflow truly requires behavior that `system` cannot provide.

## What This Module Owns

This module owns two related entities:

- `TelegramUser`
  The Telegram bot user identity record.
- `UserProfile`
  The editable profile record linked to one Telegram user.

Think of the boundary like this:

- `TelegramUser` stores Telegram-originated identity fields such as `telegram_id`, `username`, and `language_code`
- `UserProfile` stores application-level collected data such as `phone`, `email`, `timezone`, `full_name`, and `note`

If new data is coming directly from Telegram identity, it likely belongs in `TelegramUser`.
If the data is collected, enriched, or maintained by the product, it likely belongs in `UserProfile`.

## Preferred Imports

If another module only needs the exported ORM models, prefer:

```python
from app.modules.telegram_module import TelegramUser, UserProfile
```

Internal module structure should still use local imports when that keeps files simpler.

## Module Map

### `models/`

Contains the ORM models for Telegram user storage.

Important files:

- `models/telegram_user.py`
- `models/user_profile.py`

Agent expectations:

- `TelegramUser` is the source of truth for Telegram identity.
- `UserProfile` is a one-to-one extension of `TelegramUser`.
- Both models inherit shared primitives from `system`.
- Relationship changes must preserve the intended one-user-one-profile behavior.

### `schemas/`

Contains request/response DTOs for the Telegram API layer.

Important files:

- `schemas/telegram_user.py`
- `schemas/user_profile.py`

Agent expectations:

- `TelegramUserCreate` and `UserProfileCreate` are input DTOs for creation flows.
- `TelegramUserPatch` and `UserProfilePatch` are partial update DTOs.
- `TelegramUserRead` includes nested `user_profile`.
- Schema changes should stay aligned with model fields and handler response contracts.

### `services/`

Contains feature-specific business logic that wraps shared `CRUD`.

Important file:

- `services/user_service.py`

Current service responsibilities:

- idempotent Telegram user creation by `telegram_id`
- automatic creation of the linked `UserProfile`
- bulk creation for Telegram users
- login flow that updates `last_seen_at`

Agent expectations:

- Keep orchestration logic here when a workflow spans more than one model.
- Reuse `CRUD` for generic persistence and keep Telegram-specific coordination in this layer.
- Preserve rollback/cleanup behavior when multi-step creation flows fail.

### `handlers.py`

Contains the FastAPI router for Telegram endpoints.

Current routes are grouped under `/telegram` and expose:

- login
- single and bulk Telegram user creation
- CRUD-style read/update/delete for `TelegramUser`
- CRUD-style create/read/update/delete for `UserProfile`

Treat handlers as thin transport code.
If a change affects multiple models or requires business coordination, move that logic into `services/` instead of growing `handlers.py`.

### `utils/`

Currently minimal.

Only place code here if it is Telegram-specific and reused across this module.
Do not move generic utilities here if they belong in `system`.

## Data Model Contract

### `TelegramUser`

`TelegramUser` represents the Telegram-side identity.

Important fields:

- `telegram_id` is the external unique identifier and is the main idempotency key
- `username`, `first_name`, `last_name`, `language_code` store Telegram metadata
- `last_seen_at` is updated during login
- `is_blocket_bot` stores bot-block status using the current field name as implemented

Agent note:

- The field is currently named `is_blocket_bot`.
- Even if it looks like a typo, do not rename it casually because that would affect models, schemas, migrations, and API contracts.

### `UserProfile`

`UserProfile` represents collected profile data for a Telegram user.

Important fields:

- `telegram_user_id` links the profile to `TelegramUser`
- `phone`
- `email`
- `timezone`
- `full_name`
- `note`

Current relationship rules:

- each `TelegramUser` is expected to have at most one `UserProfile`
- deleting a `TelegramUser` should remove the linked profile through cascade behavior

If you modify relationship settings, verify both ORM behavior and database-level foreign key behavior together.

## Service Behavior That Must Be Preserved

### `create_telegram_user(...)`

This is not a plain insert helper.
It has an important workflow contract:

1. It uses `CRUD.get_or_create(...)` with `lookup_fields=("telegram_id",)`.
2. If the Telegram user already exists, it returns the existing row and `created=False`.
3. If the Telegram user is new, it also creates a linked `UserProfile`.
4. If profile creation fails after user creation, it attempts cleanup by deleting the just-created `TelegramUser`.

Preserve this behavior unless the product explicitly changes the lifecycle contract.

### `bulk_create_telegram_users(...)`

Bulk creation currently creates:

- many `TelegramUser` rows first
- then matching `UserProfile` rows

If profile creation fails, the service attempts cleanup of the created Telegram users.
Any bulk-flow changes should keep data consistency as the first priority.

### `login_telegram_user(...)`

Login is currently a persistence event, not only a read:

- it finds a user by `telegram_id`
- returns `404` if not found
- updates `last_seen_at`
- commits and refreshes the entity

If you change login semantics, document whether it is still read-plus-touch or becomes pure authentication lookup.

## Handler Contract

Important behavior in `handlers.py`:

- `POST /telegram/login` logs in an existing Telegram user by `telegram_id`
- `POST /telegram/users` is idempotent and returns `201` for new rows, `200` for existing rows
- `POST /telegram/users/bulk` creates multiple users and profiles
- `GET /telegram/users` and `GET /telegram/profile` rely on shared `CRUD.get(...)` pagination and search behavior
- `PATCH` and `DELETE` flows rely on shared `CRUD` contracts

If handler behavior changes, keep response codes and idempotency rules explicit in both code and docs.

## Change Rules

Good changes in this module:

- extending Telegram user or profile fields that clearly belong to this domain
- adding Telegram-specific service orchestration
- improving consistency between Telegram user creation and profile creation
- documenting API or model contracts more clearly

Avoid these changes:

- moving generic persistence logic out of `system` into this module
- adding unrelated product-specific workflows that do not belong to Telegram identity/profile storage
- bypassing service-layer cleanup for multi-step create flows
- renaming existing public fields without handling migration and schema impact

## Safety Notes

- If you add or rename model fields, update models, schemas, handlers, and migrations together.
- If you change exports, update `telegram_module/__init__.py`.
- If you change creation or login semantics, update both `README.md` and this file.
- If you add feature-specific queries beyond simple CRUD, prefer new service functions instead of overloading handlers.
- Keep search, pagination, and generic patch/delete behavior delegated to `system.CRUD` unless there is a strong Telegram-specific reason not to.

## Practical Agent Workflow

When working in or around this module:

1. Check whether the change is Telegram-domain logic or shared infrastructure logic.
2. If it is shared infrastructure, edit `system` instead of `telegram_module`.
3. If it is Telegram-specific orchestration, prefer `services/user_service.py`.
4. Keep `handlers.py` thin and transport-focused.
5. Preserve the `TelegramUser` to `UserProfile` lifecycle contract.
6. Update module documentation when behavior or exported interfaces change.

This module should stay reusable, predictable, and centered on Telegram user identity plus profile collection.
