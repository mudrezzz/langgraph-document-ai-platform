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

- Linux: `backend/scripts/demo_release_go_no_go_case.sh`
- Windows: `backend/scripts/demo_release_go_no_go_case.ps1`

## Выходные артефакты

- `output/release_packet_dataset.generated.json`
- `output/release_readiness_report.md`

Файлы `output/*.generated.json` и `output/*.md` считаются runtime-артефактами и не коммитятся в git.
