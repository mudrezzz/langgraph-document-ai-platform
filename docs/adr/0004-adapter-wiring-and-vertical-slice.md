# ADR-0004: Adapter wiring и первый vertical slice Retrieval

- Статус: Accepted
- Дата: 2026-04-17

## Контекст

После базового framework skeleton нужно было подтвердить, что архитектура действительно позволяет собирать рабочий workflow через интерфейсы, без прямой зависимости domain-логики от concrete интеграций.

## Решение

1. Ввести слой `infra/*` с concrete adapter skeleton.
2. Собирать workflow через явное dependency injection в bootstrap-модуле.
3. Реализовать первый рабочий vertical slice: `RetrievalPackWorkflow`.
4. В workflow сохранять промежуточные retrieval-артефакты (`summary`, `detail`, `rerank`) через `RetrievalTrace`.

## Последствия

Плюсы:

- проверена жизнеспособность контрактной архитектуры;
- сформирован шаблон сборки прикладного workflow;
- проще наращивать production adapters без изменения domain API.

Минусы:

- текущие concrete adapters пока не подключены к реальной инфраструктуре;
- требуется следующий инкремент для API boundary и runtime-интеграции.