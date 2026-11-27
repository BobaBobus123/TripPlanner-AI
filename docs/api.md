# API-контракт ПР14

Базовый адрес: `/api/v1`. Формы и ответы JSON используют Pydantic-модели с `extra="forbid"`. Все ответы содержат заголовок `X-Request-ID`. Можно передать собственный ID из букв, цифр, `.`, `_`, `-` (1-128 символов); иначе сервер создаёт UUID.

## `GET /health`

Liveness/readiness без вызова провайдера и без секретов.

```json
{
  "status": "ok",
  "checks": {
    "storage": "memory",
    "provider": "mock"
  }
}
```

`GET /health/live` и `GET /health/ready` доступны для отдельных проверок оркестратором.

## `POST /api/v1/plans`

Синхронно создаёт план, HTTP `201 Created`. Заголовок `X-Owner-ID` обязателен. Сейчас это демонстрационный идентификатор владельца, не механизм аутентификации.

```json
{
  "destination": "Lviv",
  "start_date": "2027-05-10",
  "end_date": "2027-05-12",
  "currency": "UAH",
  "budget": 12000,
  "traveler_count": 2,
  "interests": ["architecture"]
}
```

Ответ содержит `id`, нормализованный ввод, маршрут по каждому календарному дню, `missing_data`, `source` и `created_at`. Mock не заявляет актуальные цены, погоду или часы работы.

## `GET /api/v1/plans/{plan_id}`

Возвращает план только владельцу, указанному в `X-Owner-ID`. Несуществующий план и чужой план оба дают `404`, чтобы не раскрывать наличие чужих данных.

## Формат ошибки

```json
{
  "error": {
    "code": "invalid_request",
    "message": "Request validation failed.",
    "retryable": false,
    "request_id": "demo-request-01",
    "fields": ["end_date"]
  }
}
```

Каталог кодов: `invalid_request` (422), `not_found` (404), `rate_limited` (429), `provider_unavailable` (503), `provider_timeout` (504), `invalid_output` (502), `internal` (500). Для retryable ошибки при наличии интервала ответ также содержит `retry_after` и HTTP-заголовок `Retry-After`. Ответы не содержат traceback, пользовательских значений или деталей исключения.

## Синхронный выбор

ПР14 не создаёт асинхронную задачу, поэтому `202 Accepted`, статус/результат и отмена здесь не нужны. При внедрении реального провайдера измерения latency в ПР15 определят, нужно ли переходить на фоновый контракт.

OpenAPI-описание доступно во время запуска по `/openapi.json`; снимок контракта добавляется в ПР19.
