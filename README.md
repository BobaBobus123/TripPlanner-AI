# TripPlanner AI

Учебно-прикладной ассистент планирования поездок.

## Текущий этап

ПР14: архитектура и walking skeleton на FastAPI с mock-провайдером и in-memory хранилищем.

## Стартовые артефакты

- [Паспорт проекта](docs/passport.md)
- [Бэклог](docs/backlog.md)
- [Стартовый eval-набор](eval/cases.json)
- [Правила использования AI](AI_USAGE.md)
- [Архитектура](docs/architecture.md)
- [API-контракт](docs/api.md)

## Локальный запуск

Требуется Python 3.11 или новее.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
uvicorn tripplanner.main:app --reload
```

Откройте `http://127.0.0.1:8000/`. Swagger UI доступен по адресу `http://127.0.0.1:8000/docs`.

## Проверки

```powershell
python -m pytest
```

По умолчанию используется только детерминированный mock-провайдер; платные API не вызываются. Конфигурация задаётся переменными окружения, пример — в [.env.example](.env.example).
