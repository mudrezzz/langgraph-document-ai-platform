# ADR-0056: Document assembly workflow baseline

- Статус: Accepted
- Дата: 2026-04-25

## Контекст

После ADR-0055 section authoring уже выполнялся через typed workflow boundary, но финальная сборка документа и export по-прежнему оставались прямыми вызовами `DocumentAssembler` и `ArtifactExporter` из `AuthoringApplicationService`. Это оставляло последнюю часть authoring pipeline вне общего workflow runtime path, хотя именно здесь формируется итоговый content/format payload, который затем сохраняется как artifact.

## Решение

1. Добавить `domain_authoring.DocumentAssemblyWorkflow` как baseline workflow поверх существующих `DocumentAssembler` и `ArtifactExporter`.
2. Использовать typed `AssemblyWorkflowState` и multi-node path:
   - `assemble_document`;
   - `export_artifact`;
   - `finalize_document`.
3. Перевести `AuthoringApplicationService` на вызов final assembly/export через новый workflow boundary, сохранив внешние authoring API и artifact payload contracts.
4. Оставить workflow детерминированным и синхронным на этом шаге: без отдельного persistence/read-model слоя и без отдельного публичного endpoint.
5. Сохранить reuse существующих domain services/adapters, не вводя параллельную архитектуру assembly/export.

## Последствия

Плюсы:

- весь deterministic authoring path теперь проходит через workflow boundaries и опирается на единый framework runtime pattern;
- появляется явная точка роста для будущих document-level quality gates, HITL assembly review и persisted workflow audit;
- `AuthoringApplicationService` меньше зависит от прямых service call и остается orchestration layer.

Минусы:

- workflow пока не имеет собственного persisted state/read-model слоя;
- resume path пока делает только baseline re-assembly, без отдельного planner для selective document rewrite;
- final artifact по-прежнему публикуется через существующий artifact service, а не через отдельный document workflow boundary API.
