# Архітектура TripPlanner AI

## Контекст

TripPlanner створює структуровані чернетки маршрутів. Користувач входить, формує запит, отримує фактичні етапи обробки та повертається до збереженого результату. Сервіс не підтверджує актуальність погоди, цін і годин роботи без зовнішнього джерела.

```mermaid
flowchart LR
    User[Мандрівник] -->|HTTPS / браузер| Web[FastAPI + HTML]
    Web -->|Cookie-сесія + CSRF| Auth[Автентифікація]
    Web -->|202 / статус / SSE| Jobs[API задач]
    Jobs -->|атомарна черга / історія| DB[(SQLite локально / PostgreSQL production)]
    Worker[Фоновий worker] -->|claim / lease / події| DB
    Worker -->|структурований запит| Provider[Провайдер маршрутів]
    Provider -->|чернетка| Worker
    Worker -->|валідація / план / завершення| DB
    Web -->|SSE та відновлення стану| User
```

Локально `STORAGE_BACKEND=sqlite` зберігає облікові записи, сесії, завдання, події й плани у файлі та запускає worker у процесі вебзастосунку. Для production вебзастосунок і окремий worker використовують спільний PostgreSQL через `DATABASE_URL`.

## Потік запиту

1. `AuthService` створює обліковий запис із Argon2-хешем пароля. Після успішного входу створюється серверна сесія; підтвердження пошти не є обов’язковим.
2. FastAPI перевіряє `PlanRequest`, генерує fingerprint і атомарно створює завдання за унікальністю `(user_id, idempotency_key)`.
3. Worker забирає чергу через `FOR UPDATE SKIP LOCKED`, записує lease та подію `preparing`.
4. Оркестратор повідомляє про генерацію та перевірку лише під час реального виконання цих фаз; текст моделі не віддається через SSE.
5. Транзакція зберігає план і переводить задачу в `completed`. Скасування синхронізується блокуванням рядка, тому пізній результат не перезаписує `cancelled`.
6. SSE читає журнал `job_events`, підтримує `Last-Event-ID`, heartbeat і перепідключення. API статусу є джерелом відновлення після оновлення сторінки.
7. Після втрати lease активна задача позначається `interrupted`, а не запускається повторно: повторний платний виклик без згоди користувача не виконується.

## Контейнери й протоколи

```mermaid
flowchart TB
    Browser[Браузер: український інтерфейс] -->|JSON, Cookie, CSRF| API[FastAPI]
    Browser -->|SSE / Last-Event-ID| API
    API --> Auth[AuthService / Argon2]
    API --> Store[TripPlannerStore]
    Worker[python -m tripplanner.worker] --> Store
    Store --> SQLite[SQLiteTripPlannerStore: локально]
    Store --> Postgres[PostgresTripPlannerStore: Railway]
    Worker --> Orchestrator[PlanOrchestrator]
    Orchestrator --> Provider[PlanProvider]
    Provider --> Mock[MockProvider]
    Provider --> Compat[OpenAI-сумісний провайдер]
    Settings[Змінні середовища] --> API
    Settings --> Worker
```

Контролер не імпортує SDK провайдера й не довіряє `X-Owner-ID`. Сховище зберігає лише хеші сесійного bearer-токена; запити власника обмежуються перевіреним `user_id`. CSRF-токен повертається тільки після входу або через same-origin endpoint `/auth/me` і потрібен для всіх автентифікованих змінювальних запитів.

## Межі та відомі обмеження

- Argon2, випадкові сесії, відкликання, CSRF/origin-перевірка та обмеження частоти входу реалізовані.
- Реєстрація не вимагає SMTP чи підтвердження пошти. Відновлення пароля й видалення облікового запису залишаються обмеженнями.
- Worker використовує lease й не повторює перервані задачі автоматично.
- SQLite зберігається між перезапусками процесу; у production конфігурація вимагає PostgreSQL.
- Інтерфейс не показує штучні відсотки. Повідомлення етапу створюється лише фактичним кодом worker/orchestrator.
- Реальні інтеграційні тести з Railway PostgreSQL і браузерні автоматизовані e2e ще потребують середовища/налаштування; локальні API та ручний браузерний сценарій перевіряються окремо.

Початковий файл діаграм: [docs/diagrams/architecture.mmd](diagrams/architecture.mmd).
