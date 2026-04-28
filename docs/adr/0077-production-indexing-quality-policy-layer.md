# ADR-0077: Production indexing quality policy layer

- Статус: Accepted
- Дата: 2026-04-28

## Контекст

После ADR-0072/0073/0075/0076 canonical ingestion уже покрывает parser diagnostics, OCR fallback, table-aware provenance и version-aware read-model. При этом quality gate для indexing оставался локальной функцией в `KnowledgeIndexingApplicationService` с hardcoded blocking flags.

Такой подход ограничивал production hardening:

- policy нельзя было конфигурировать через runtime env без правок кода;
- нет typed per-document решения (`accepted/rejected`) для partial indexing;
- quality summary был слабосвязан с parser diagnostics и policy metadata.

## Решение

1. Ввести отдельный domain-level policy слой `KnowledgeIndexingQualityPolicy` (`domain_docs.indexing.quality_policy`).
2. Policy возвращает typed aggregated decision `IndexingQualityPolicyDecision` и per-document decisions `IndexingDocumentQualityDecision`:
   - `gate_status`;
   - `accepted/rejected` по документам;
   - `blocking_flags` / `warning_flags`;
   - `accepted_doc_ids` / `rejected_doc_ids`.
3. `KnowledgeIndexingApplicationService` применяет policy до persistence workflow:
   - rejected documents не передаются в `KnowledgeIndexingWorkflow`;
   - embeddings индексируются только для accepted documents;
   - parser diagnostics остаются доступными для всех parsed documents в task details/reporting.
4. `ApiContainer` собирает policy из env:
   - `APP_INDEXING_QUALITY_POLICY_NAME`;
   - `APP_INDEXING_QUALITY_BLOCKING_FLAGS` (CSV);
   - `APP_INDEXING_QUALITY_WARNING_ONLY_FLAGS` (CSV);
   - `APP_INDEXING_ALLOW_RECOVERED_OCR`;
   - `APP_INDEXING_OCR_RECOVERY_BLOCKING_FLAG`;
   - `APP_INDEXING_OCR_RECOVERY_SUCCESS_FLAG`.
5. Публичные API endpoints не меняются; quality fields расширяются аддитивно внутри `quality_summary`.

## Последствия

Плюсы:

- quality gate для canonical indexing стал конфигурируемым production policy layer;
- partial-blocking behavior формализован и тестируем;
- runtime может смягчать/ужесточать gates без изменения workflow contracts.

Минусы:

- policy пока env-driven и не вынесен в отдельный persisted configuration domain;
- при `gate_status=failed` задача по-прежнему может завершиться `completed`, если есть accepted documents (операционный fail-fast policy может быть добавлен отдельным срезом).
