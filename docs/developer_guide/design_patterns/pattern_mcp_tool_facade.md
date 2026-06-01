# Design Pattern: MCP Tool Facade

Update date: 2026-06-02
Status: Active

## 1. Goal

Expose agent capabilities as MCP-style tools while keeping business logic in a transport-agnostic core agent layer.

## 2. Why this matters

Without this split, MCP handlers often become a second implementation of business logic.
That increases divergence risk between:

1. in-process path;
2. MCP path;
3. future API path.

This pattern prevents that drift.

## 3. Structure contract

- Core agent (domain/workflow composition):
  - `agent_examples/patterns/mcp_tool_facade/agent.py` (`McpToolFacadeCoreAgent`)
- MCP-style adapter:
  - `agent_examples/patterns/mcp_tool_facade/agent.py` (`InProcessMcpToolFacadeAdapter`)
- Workflow call:
  - `agent_examples/patterns/mcp_tool_facade/workflow.py`
- Tool registry helpers:
  - `agent_examples/patterns/mcp_tool_facade/tools.py`

## 4. Tool contract

Exposed tools:

1. `search_evidence` (`action`)
2. `get_service_metadata` (`read`)

Adapter responsibilities:

1. payload validation;
2. tool dispatch;
3. metadata envelope (`tool_name`, `called_at`, `result`).

Core responsibilities:

1. query execution over workflow;
2. evidence/result shaping.

## 5. Run and verify

```bash
.venv/bin/python agent_examples/run_example.py --pattern mcp_tool_facade
.venv/bin/pytest -q agent_examples/patterns/mcp_tool_facade/tests/test_agent.py
```

