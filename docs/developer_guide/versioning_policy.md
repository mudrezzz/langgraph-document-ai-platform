# Versioning & Deprecation Policy

Дата обновления: 2026-04-30  
Статус: Active (P1 policy)

Политика определяет, как проект версионирует документацию и публичные контракты API/MCP.

## 1. Contract surface authority

Источник границ стабильности:

- `docs/developer_guide/public_contract_surface.md`
- `docs/developer_guide/api_reference.md`
- `docs/developer_guide/mcp_reference.md`

Если изменение не отражено в этих документах, оно не считается официальным обновлением public contract.

## 2. Stability levels

- `Stable`: поддерживаемые контракты; breaking changes запрещены без deprecation окна.
- `Experimental`: допускаются breaking changes между инкрементами.
- `Internal`: без внешних гарантий совместимости.

## 3. Versioning units

Проект использует два независимых слоя версионирования:

1. Документационный инкремент (`README`, architecture status, backlog notes).
2. Contract surface version (`public_contract_surface vN`).

Рекомендованный принцип:

- additive change в stable contract -> `vN` (минорное обновление описания);
- breaking change в stable contract -> `vN+1` + deprecation window и migration notes.

## 4. Deprecation policy

Для stable API/MCP contracts:

1. Объявить deprecation в docs (`public_contract_surface`, reference docs, changelog note).
2. Сохранить старый контракт минимум на один documentation increment, если это технически возможно.
3. Добавить migration path (что поменять клиенту).
4. После removal обновить:
   - `public_contract_surface`
   - `api_reference`/`mcp_reference`
   - `docs/DOCS_BACKLOG.md`

Для experimental contracts deprecation окно может быть сокращено, но migration note обязателен.

## 5. Breaking change checklist

Перед внесением breaking change в stable surface:

1. Подтвердить необходимость и scope.
2. Обновить policy docs и references.
3. Добавить/обновить smoke/tests, подтверждающие новый контракт.
4. Обновить release docs с triage и rollback note.

## 6. Version tags in docs

Рекомендуется помечать ключевые документы:

- `Дата обновления`
- `Статус`
- при необходимости `Contract Surface: vN`

Это снижает рассинхронизацию между кодом и документацией при быстрых инкрементах.
