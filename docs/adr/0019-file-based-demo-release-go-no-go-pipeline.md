# ADR-0019: File-Based Demo Pipeline для Release Go/No-Go

- Статус: Accepted
- Дата: 2026-04-20

## Контекст

Текущий референсный demo (`saa_release_readiness`) опирался на заранее подготовленный JSON-датасет и плохо показывал сценарий, близкий к рабочей эксплуатации: входной документ -> подготовка retrieval-слоя -> запуск задачи -> артефакт для принятия решения.

Для ручного smoke на сервере требовался более реалистичный, но компактный пример с осмысленным результатом, который можно интерпретировать без чтения внутреннего JSON.

## Решение

1. Добавить новый demo-кейс `release_go_no_go_case` с входом в формате markdown:
   - `backend/examples/cases/release_go_no_go_case/input/release_packet.md`.
2. Ввести конвертер markdown -> retrieval dataset:
   - `build_release_packet_dataset(...)` в `domain_rag.retrieval.release_packet_dataset`;
   - CLI-скрипт `backend/scripts/build_release_packet_dataset.py`.
3. Использовать существующий контракт `task_context.case_dataset_path` для запуска retrieval по файлу датасета.
4. Добавить post-processing шаг demo:
   - скрипт `backend/scripts/build_release_readiness_report.py`;
   - выходной артефакт `release_readiness_report.md` с GO/NO-GO, блокерами, approvals, источниками evidence и сводкой task events.
5. Добавить end-to-end demo-оркестратор:
   - Linux: `backend/scripts/demo_release_go_no_go_case.sh`;
   - Windows: `backend/scripts/demo_release_go_no_go_case.ps1`.
6. Усилить стабильность smoke/demo запуска:
   - приоритет локального `./.venv` интерпретатора;
   - явная проверка наличия `uvicorn` до старта API.

## Последствия

Плюсы:

- demo стал ближе к реальному пользовательскому потоку с файловым входом;
- результат прогона теперь интерпретируется через человекочитаемый отчет, а не только через JSON;
- ручной прогон на Ubuntu/Windows стал стабильнее за счет предсказуемого выбора Python-окружения.

Минусы:

- конвертер markdown пока заточен под структуру release packet (не универсальный parser для любых документов);
- итоговый отчет использует эвристики по тексту (blockers/pending approvals), без LLM-оценки и без отдельного authoring workflow.
