# ADR-0038: Workflow node specs and subgraph context propagation

- Status: Accepted
- Date: 2026-04-24

## Context

After the first framework increments, `BaseWorkflow` was already executed through the LangGraph runtime, but actually compiled a one-step graph, which delegated all the work to `execute()` or `execute_resume()`. This was sufficient for early retrieval/indexing slices, but rather weak for the target architecture:

- domain workflows must be explicitly multi-node;
- reusable subgraphs must pass parent workflow metadata;
- node-level audit and observability require a stable `node_name`;
- `task_id` and `correlation_id` must be available inside node handlers.

## Solution

1. Add `WorkflowExecutionContext`:
   - `workflow_name`;
   - `node_name`;
   - `task_id`;
   - `correlation_id`;
   - `is_resume`;
   - `metadata`.
2. Add `WorkflowNodeSpec`:
   - `name`;
   - `handler`;
   - `next_node`.
3. Expand `BaseWorkflow.workflow_nodes(is_resume=...)`.
4. Save backward compatibility:
- default `workflow_nodes` builds the same single-node graph;
- existing subclasses that only override `execute/execute_resume` continue to work.
5. Compile LangGraph invoke/resume graphs from sequential node specs.
6. Execute the same node specs in fallback runtime.
7. Improve `SubgraphWorkflow`:
   - `subgraph_name`;
   - `invoke_as_subgraph(...)`;
- parent context propagation via `task_context`.

## Consequences

Pros:

- domain workflows can now declare explicit framework-level nodes without rewriting compile/invoke/checkpointer logic;
- node handlers receive typed context with task/correlation metadata;
- `SubgraphWorkflow` has become a useful reusable base, rather than an empty subclass marker;
- the next slice can add node-level task events on top of the stable `node_name`.

Cons:

- the current implementation supports sequential graph specs; conditional routing remains the task of the next slices;
- parent context propagation works through `task_context` and requires state schemas in which such a field is present.
