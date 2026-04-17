# SAA Release Readiness Case

Этот пример имитирует близкий к реальности сценарий подготовки evidence pack для раздела ТЗ по readiness к релизу.

## Входные данные

- `input/knowledge_layers.json`

Файл содержит summary/detail knowledge layers и метаданные источников.

## Как запускать

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\demo_saa_release_readiness_case.ps1
```

Скрипт поднимет API, выполнит retrieval задачу по кейсу и выведет краткий отчет по evidence.