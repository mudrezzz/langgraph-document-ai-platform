# mcp_tool_facade - agent logic behind MCP-style tools

Pattern that demonstrates a strict split:

1. Core agent logic (domain/workflow composition).
2. MCP-style adapter layer exposing core operations as tools.

## Why this pattern exists

Use this pattern when you want the same agent logic to be reusable from:

- in-process Python calls;
- MCP transport adapter;
- future API wrappers.

The key rule: transport adapter should not contain business logic.

## Structure

- `agent.py`:
  - `McpToolFacadeCoreAgent` (core logic);
  - `InProcessMcpToolFacadeAdapter` (MCP-style tool facade).
- `workflow.py`: core retrieval workflow call.
- `tools.py`: adapter helper utilities and tool registry contract.
- `main.py`: runnable demo of one tool call.

## Run

```bash
.venv/bin/python agent_examples/patterns/mcp_tool_facade/main.py
```

Through the general runner:

```bash
.venv/bin/python agent_examples/run_example.py --pattern mcp_tool_facade
```

Dry-run:

```bash
.venv/bin/python agent_examples/run_example.py --pattern mcp_tool_facade --dry-run
```

## Output proof

- `agent_examples/patterns/mcp_tool_facade/expected_output/result.example.json`

## Tests

```bash
.venv/bin/pytest -q agent_examples/patterns/mcp_tool_facade/tests/test_agent.py
```

