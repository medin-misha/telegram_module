# Telegram Module

`telegram_module` - это прикладной модуль `fastapi_template` для хранения Telegram-пользователей и связанных с ними профилей.

Модуль используется как единая точка для:

- хранения Telegram-identity в модели `TelegramUser`;
- хранения прикладных данных профиля в модели `UserProfile`;
- идемпотентного создания Telegram-пользователей по `telegram_id`;
- обновления `last_seen_at` при логине;
- HTTP-эндпоинтов для CRUD-операций над Telegram-пользователями и профилями.

Модуль опирается на инфраструктуру из `app.modules.system` и не должен дублировать общие CRUD- и DB-error-механизмы локально.

## Структура

```text
telegram_module/
├── __init__.py
├── handlers.py
├── models/
│   ├── __init__.py
│   ├── telegram_user.py
│   └── user_profile.py
├── schemas/
│   ├── __init__.py
│   ├── telegram_user.py
│   └── user_profile.py
├── services/
│   ├── __init__.py
│   └── user_service.py
├── utils/
└── README.md
```

## Зависимость от `system`

`telegram_module` построен поверх `system` и повторно использует его общие примитивы:

- `Base` и `TimestampMixin` для ORM-моделей;
- `CRUD` для типовых операций create/get/patch/delete;
- `DBErrorHandler` для нормализации ошибок SQLAlchemy.

Предпочтительные импорты:

```python
from app.modules.system import Base, TimestampMixin, CRUD
from app.modules.system.services.errors import DBErrorHandler
```


## Граница ответственности

Модуль владеет двумя сущностями:

- `TelegramUser` - Telegram-identity пользователя;
- `UserProfile` - прикладной профиль, связанный с Telegram-пользователем.

Разделение ответственности такое:

- поля, приходящие из Telegram как внешней системы, должны жить в `TelegramUser`;
- поля, которые собирает или изменяет само приложение, должны жить в `UserProfile`.

Практически это означает:

- `telegram_id`, `username`, `first_name`, `last_name`, `language_code` относятся к `TelegramUser`;
- `phone`, `email`, `timezone`, `full_name`, `note` относятся к `UserProfile`.

## Основные модели

### `TelegramUser`

Находится в [models/telegram_user.py](/home/misha/code/module_service/fastapi_template/app/modules/telegram_module/models/telegram_user.py).

`TelegramUser` хранит Telegram-identity и статус активности пользователя.

Ключевые поля:

- `telegram_id: int` - внешний уникальный идентификатор Telegram-пользователя;
- `username: str | None` - username в Telegram;
- `first_name: str | None`;
- `last_name: str | None`;
- `language_code: str | None` - языковой код Telegram-клиента;
- `last_seen_at: datetime | None` - последнее время логина/касания пользователя;
- `is_blocket_bot: bool` - текущий флаг блокировки бота.

Модель содержит связь:

- `user_profile` - one-to-one профиль пользователя;
- связь настроена через `uselist=False`;
- загрузка профиля идет через `lazy="selectin"`.

### `UserProfile`

Находится в [models/user_profile.py](/home/misha/code/module_service/fastapi_template/app/modules/telegram_module/models/user_profile.py).

`UserProfile` хранит прикладные данные, связанные с Telegram-пользователем.

Ключевые поля:

- `telegram_user_id: int` - внешний ключ на `TelegramUser`;
- `phone: str | None`;
- `email: str | None`;
- `timezone: str | None`;
- `full_name: str | None`;
- `note: str | None`.

Текущие правила связи:

- у одного `TelegramUser` ожидается не более одного `UserProfile`;
- `UserProfile.telegram_user_id` использует `ForeignKey(..., ondelete="CASCADE")`;
- удаление `TelegramUser` должно удалять и связанный профиль.

Если меняется конфигурация relationship или foreign key, нужно проверять и ORM-поведение, и фактическое поведение базы данных.

## Pydantic-схемы

Схемы находятся в:

- [schemas/telegram_user.py](/home/misha/code/module_service/fastapi_template/app/modules/telegram_module/schemas/telegram_user.py)
- [schemas/user_profile.py](/home/misha/code/module_service/fastapi_template/app/modules/telegram_module/schemas/user_profile.py)

Основные DTO:

- `TelegramUserCreate` - входная схема создания Telegram-пользователя;
- `TelegramUserLogin` - схема логина по `telegram_id`;
- `TelegramUserPatch` - частичное обновление Telegram-пользователя;
- `TelegramUserRead` - чтение Telegram-пользователя с вложенным `user_profile`;
- `UserProfileCreate` - создание профиля;
- `UserProfilePatch` - частичное обновление профиля;
- `UserProfileRead` - схема чтения профиля.

При изменении моделей нужно синхронно обновлять и схемы, чтобы не расходились ORM-структура и API-ответы.

## Сервисный слой

Сервисная логика находится в [services/user_service.py](/home/misha/code/module_service/fastapi_template/app/modules/telegram_module/services/user_service.py).

Здесь собрана Telegram-специфичная orchestration-логика поверх `CRUD`.

### `create_telegram_user(...)`

Это не просто insert-обертка.

Контракт функции:

1. вызывает `CRUD.get_or_create(...)` с `lookup_fields=("telegram_id",)`;
2. если пользователь уже существует, возвращает его и `created=False`;
3. если пользователь создан впервые, дополнительно создаёт пустой `UserProfile`;
4. если создание профиля падает, пытается удалить только что созданный `TelegramUser`.

За счёт этого `POST /telegram/users` остается идемпотентным.

### `bulk_create_telegram_users(...)`

Сначала создает набор `TelegramUser`, потом создает для них `UserProfile`.

Если создание профилей падает, сервис пытается удалить ранее созданных пользователей, чтобы не оставить систему в промежуточном состоянии.

### `login_telegram_user(...)`

Логин в текущей реализации - это не просто чтение.

Функция:

- ищет пользователя по `telegram_id`;
- возвращает `404`, если он не найден;
- обновляет `last_seen_at`;
- делает `flush()` и `refresh()`.

Если семантика логина меняется, это важно отразить и в коде, и в документации.

## HTTP API

Router находится в [handlers.py](/home/misha/code/module_service/fastapi_template/app/modules/telegram_module/handlers.py) и объявлен с префиксом `/telegram`.

### TelegramUser endpoints

- `POST /api/telegram/login` - логин существующего пользователя по `telegram_id`;
- `POST /api/telegram/users` - идемпотентное создание пользователя;
- `POST /api/telegram/users/bulk` - массовое создание пользователей;
- `GET /api/telegram/users/{id}` - получение пользователя по внутреннему `id`;
- `GET /api/telegram/users` - список пользователей с пагинацией и поиском;
- `PATCH /api/telegram/users/{id}` - частичное обновление пользователя;
- `DELETE /api/telegram/users/{id}` - удаление пользователя.

Поведение `POST /api/telegram/users`:

- `201 Created`, если пользователь был создан;
- `200 OK`, если пользователь с таким `telegram_id` уже существовал.

### UserProfile endpoints

- `POST /api/telegram/profile` - создание профиля;
- `GET /api/telegram/profile/{id}` - получение профиля по внутреннему `id`;
- `GET /api/telegram/profile` - список профилей с пагинацией и поиском;
- `PATCH /api/telegram/profile/{id}` - частичное обновление профиля;
- `DELETE /api/telegram/profile/{id}` - удаление профиля.

Списковые `GET`-эндпоинты используют общий `CRUD.get(...)`, поэтому наследуют стандартное поведение `system`:

- `page` и `limit` для пагинации;
- `search` для поиска;
- `field` для поиска по конкретному полю.

## Экспорт модуля

В [telegram_module/__init__.py](/home/misha/code/module_service/fastapi_template/app/modules/telegram_module/__init__.py) наружу экспортируются:

- `TelegramUser`
- `UserProfile`

Предпочтительный импорт моделей из других модулей:

```python
from app.modules.telegram_module import TelegramUser, UserProfile
```

## Правила изменений

Хорошие изменения в этом модуле:

- добавление полей, которые действительно относятся к Telegram-identity или профилю;
- расширение сервисной логики, если она координирует несколько моделей;
- улучшение согласованности между созданием `TelegramUser` и `UserProfile`;
- уточнение API-контрактов и документации.

Нежелательные изменения:

- перенос общей инфраструктурной логики из `system` в `telegram`;
- разрастание `handlers.py` бизнес-логикой;
- обход сервисного слоя в сценариях, где важны cleanup и целостность данных;
- переименование публичных полей без миграций и синхронного обновления схем.

## Практические заметки

- если меняется модели, синхронно обновляйте `models`, `schemas`, `handlers` и миграции;
- если меняется экспорт, обновляйте `telegram_module/__init__.py`;
- если меняется поведение логина или создания пользователя, обновляйте и `README.md`, и `AGENTS.md`;
- если логика затрагивает несколько сущностей, держите координацию в `services/user_service.py`, а не в `handlers.py`.
