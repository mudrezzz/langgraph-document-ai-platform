# External Developer Guide

Дата обновления: 2026-04-30
Статус: Increment 32+ documentation release (slice 3)

Этот раздел - единая точка входа для внешнего разработчика, который хочет использовать backend/framework библиотеку как production retrieval + authoring platform на LangGraph.

## 1. Ролевой entrypoint

Единый маршрут чтения по ролям:

1. Integrator:
   - `docs/developer_guide/quickstart.md`
   - `docs/developer_guide/manual_demo_checks.md`
   - `docs/developer_guide/canonical_e2e_walkthrough.md`
   - `docs/developer_guide/api_reference.md`
   - `docs/developer_guide/mcp_reference.md`
   - `docs/developer_guide/env_config_reference.md`
   - `docs/developer_guide/public_contract_surface.md`
2. Contributor (framework/domain extension):
    - `docs/developer_guide/framework_concepts.md`
    - `docs/developer_guide/api_reference.md`
    - `docs/developer_guide/mcp_reference.md`
    - `docs/developer_guide/env_config_reference.md`
    - `docs/developer_guide/extension_handbook.md`
    - `docs/developer_guide/public_contract_surface.md`
    - `docs/developer_guide/extension_recipes.md`
    - `docs/framework_extension_guide.md`
3. Maintainer (runtime/release):
   - `docs/developer_guide/operations_and_release.md`
   - `docs/developer_guide/release_reproducible_flow.md`
   - `docs/production_runbook.md`
   - `backend/scripts/README.md`

## 2. Что считается стабильным публичным контрактом

- FastAPI endpoints в `backend/apps/api` и их payload contracts в `README.md`.
- Framework extension path из `docs/framework_extension_guide.md`.
- Production runtime path из `docs/production_runbook.md`.
- Release acceptance scripts из `backend/scripts/*`.
- Версионированная матрица stable/experimental: `docs/developer_guide/public_contract_surface.md`.

## 3. Что этот гайд не заменяет

- Не заменяет архитектурный overview: `docs/architecture/System_Architecture_Overview.md`.
- Не заменяет историю архитектурных решений (ADR): `docs/adr/README.md`.
- Не заменяет детальный ручной smoke runbook: `docs/manual_smoke_postgres_runbook.md`.

## 4. Рекомендуемый learning path для нового разработчика

1. `quickstart.md`: поднять контур и выполнить первый retrieval smoke.
2. `public_contract_surface.md`: зафиксировать границы stable/experimental перед изменениями.
3. `framework_concepts.md`: зафиксировать execution model (runtime, async plane, HITL, quality gates).
4. `canonical_e2e_walkthrough.md`: пройти полный path documents -> indexing -> retrieval -> authoring -> HITL -> artifact.
5. `api_reference.md`: сверить endpoint-ы, payload contracts и error mapping.
6. `mcp_reference.md`: сверить MCP tools/scopes/roles и error semantics.
7. `env_config_reference.md`: зафиксировать env-профиль перед запуском или деплоем.
8. `manual_demo_checks.md`: убедиться в canonical indexing и реальном PDF/PPTX parsing path.
9. `extension_handbook.md`: выбрать нужный playbook расширения (workflow/tool/MCP/persistence/domain).
10. `extension_recipes.md`: добавить свой workflow/tool/MCP по текущим framework contracts.
11. `release_reproducible_flow.md`: выполнить линейный reproducible release path.
12. `operations_and_release.md`: прогнать release decision gate как final quality barrier.
