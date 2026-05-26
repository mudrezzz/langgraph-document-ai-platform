# langgraph-dai

Core framework, schemas, and OpenRouter adapter for building document-centric LangGraph agents.

## Install

Install latest from `main`:

```bash
pip install "langgraph-dai @ git+https://github.com/mudrezzz/langgraph-document-ai-platform.git@main#subdirectory=backend/packages"
```

Install pinned release:

```bash
pip install "langgraph-dai @ git+https://github.com/mudrezzz/langgraph-document-ai-platform.git@v0.1.0#subdirectory=backend/packages"
```

## Included packages

- `framework`
- `schemas`
- `infra.openrouter`

## Not included

- FastAPI backend
- PostgreSQL/pgvector runtime
- Celery/Redis worker
- full MCP services

## Minimal example

```python
from framework.workflows.base import BaseWorkflow, WorkflowNodeSpec
from framework.models.interfaces import IChatModelGateway
from schemas.rag.contracts import EvidencePack
from infra.openrouter.chat_gateway import OpenRouterChatModelGateway
```
