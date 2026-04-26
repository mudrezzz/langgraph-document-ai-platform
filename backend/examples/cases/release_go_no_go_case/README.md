# Release Go/No-Go Case

Мини-кейс для демонстрации file-based входа в retrieval pipeline.

## Вход

- `input/release_packet.md` — реалистичный релизный пакет по фиче Payments v2.

## Что демонстрирует

1. Конвертацию markdown-файла в retrieval dataset (`build_release_packet_dataset.py`).
2. Запуск retrieval задачи через API с `case_dataset_path`.
3. Получение осмысленного артефакта `release_readiness_report.md`:
   - GO/NO-GO решение;
   - блокеры;
   - незакрытые approvals;
   - evidence источники;
   - summary по task events.

## Основной скрипт демо

- Sync demo Linux: `backend/scripts/demo_release_go_no_go_case.sh`
- Sync demo Windows: `backend/scripts/demo_release_go_no_go_case.ps1`
- Async demo Linux: `backend/scripts/demo_release_go_no_go_async_case.sh`

Async demo использует тот же `release_packet.md`, но запускает retrieval через `POST /api/v1/tasks/retrieval/start_async` и позволяет руками увидеть `queued -> completed` lifecycle на том же кейсе.

## Выходные артефакты

- `output/release_packet_dataset.generated.json`
- `output/release_readiness_report.md`
- `output/release_readiness_report_async.md`

Файлы `output/*.generated.json` и `output/*.md` считаются runtime-артефактами и не коммитятся в git.
