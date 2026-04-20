# ADR-0020: Multi-File Ingestion и Retrieval MCP MVP

- Статус: Accepted
- Дата: 2026-04-20

## Контекст

После `Increment 14` retrieval поддерживал встроенные датасеты (`case_dataset_id`) и file-based JSON (`case_dataset_path`), но в реальных ручных прогонах вход обычно приходит как набор документов, а не один заранее собранный JSON.

Также в архитектурном плане требовался первый рабочий FastMCP runtime сервис для постепенного перехода от API-only boundary к MCP boundary.

## Решение

1. Добавить новый режим источника данных `task_context.case_dataset_dir`:
   - ingestion директории с файлами `.md/.txt/.json`;
   - построение summary/detail блоков в runtime без промежуточной ручной сборки JSON.
2. Зафиксировать приоритет источников retrieval dataset:
   - `case_dataset_path` -> `case_dataset_dir` -> `case_dataset_id`.
3. Добавить новый realistic demo-case:
   - `backend/examples/cases/release_go_no_go_multifile_case`.
4. Добавить Retrieval MCP MVP:
   - `apps/mcp_retrieval/main.py`;
   - `FastMcpRetrievalService`;
   - минимальный MCP tool `build_evidence_pack`.
5. Обновить smoke/demo контур:
   - `smoke_retrieval_api.sh/.ps1` поддерживают `case_dataset_dir`.

## Последствия

Плюсы:

- ручной smoke/demo ближе к реальной эксплуатации (несколько входных артефактов);
- retrieval API получает более гибкий ingestion-контур без поломки текущих путей;
- в системе появился первый рабочий MCP runtime boundary для retrieval домена.

Минусы:

- ingestion пока покрывает только `.md/.txt/.json` (без PDF/DOCX/OCR);
- Retrieval MCP пока содержит минимальный набор tool-ов и не закрывает полный контракт blueprint;
- для production MCP-нужд потребуются auth/rate-limit/observability политики и отдельный deploy profile.
