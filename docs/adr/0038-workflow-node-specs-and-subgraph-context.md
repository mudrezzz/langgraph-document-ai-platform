# ADR-0038: Workflow node specs и subgraph context propagation

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

После первых framework инкрементов `BaseWorkflow` уже исполнялся через LangGraph runtime, но фактически компилировал одношаговый graph, который делегировал всю работу в `execute()` или `execute_resume()`. Это было достаточно для ранних retrieval/indexing slices, но слабовато для целевой архитектуры:

- domain workflows должны быть явно multi-node;
- reusable subgraphs должны передавать parent workflow metadata;
- node-level audit и observability требуют стабильного `node_name`;
- `task_id` и `correlation_id` должны быть доступны внутри node handlers.

## Решение

1. Добавить `WorkflowExecutionContext`:
   - `workflow_name`;
   - `node_name`;
   - `task_id`;
   - `correlation_id`;
   - `is_resume`;
   - `metadata`.
2. Добавить `WorkflowNodeSpec`:
   - `name`;
   - `handler`;
   - `next_node`.
3. Расширить `BaseWorkflow.workflow_nodes(is_resume=...)`.
4. Сохранить backward compatibility:
   - default `workflow_nodes` строит прежний одноузловой graph;
   - existing subclasses, которые переопределяют только `execute/execute_resume`, продолжают работать.
5. Компилировать LangGraph invoke/resume graphs из sequential node specs.
6. Исполнять те же node specs в fallback runtime.
7. Доработать `SubgraphWorkflow`:
   - `subgraph_name`;
   - `invoke_as_subgraph(...)`;
   - parent context propagation через `task_context`.

## Последствия

Плюсы:

- domain workflows теперь могут объявлять явные framework-level nodes без переписывания compile/invoke/checkpointer логики;
- node handlers получают typed context с task/correlation metadata;
- `SubgraphWorkflow` стал полезной reusable базой, а не пустым subclass marker;
- следующий slice может добавить node-level task events поверх стабильного `node_name`.

Минусы:

- текущая реализация поддерживает sequential graph specs; conditional routing остается задачей следующих slices;
- parent context propagation работает через `task_context` и требует state schemas, в которых такое поле присутствует.
