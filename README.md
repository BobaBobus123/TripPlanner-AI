# TripPlanner AI

Учебно-прикладной ассистент планирования поездок.

## Текущий этап

ПР15: основной AI-сценарий, OpenAI-compatible provider, versioned prompt, валидация структурированного плана и офлайн evaluation.

## Стартовые артефакты

- [Паспорт проекта](docs/passport.md)
- [Бэклог](docs/backlog.md)
- [Стартовый eval-набор](eval/cases.json)
- [Правила использования AI](AI_USAGE.md)
- [Архитектура](docs/architecture.md)
- [API-контракт](docs/api.md)
- [Замеры провайдера](docs/measurements.md)

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

По умолчанию используется только детерминированный mock-провайдер; платные API не вызываются. Для подключения OpenAI-compatible endpoint задайте `PROVIDER=openai_compat`, `OPENAI_COMPAT_API_KEY`, URL/model и актуальные цены токенов. Конфигурация задаётся переменными окружения, пример — в [.env.example](.env.example).

Офлайн eval (без HTTP и реального API), результаты сохраняются в игнорируемый `eval/runs/`:

```powershell
python -m scripts.run_eval --k 3
```

Для управляемого replay/record используйте `RECORDED_MODE=replay|record|passthrough`. `record` сохраняет hash ключа и сгенерированный ответ локально; используйте только синтетические данные и не публикуйте каталог `recordings/`.
