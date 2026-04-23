from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from framework.agents.interfaces import AgentContext, AgentResult, IAgent
from framework.agents.specialized import HumanGateAgent, ReviewAgent, SupervisorAgent, ToolAgent
from framework.db.repository import BaseRepository, DummyUnitOfWork, RepositoryFactory
from framework.mcp.service import BaseFastMcpService
from framework.models.interfaces import IChatModelGateway
from framework.stores.base import BaseArtifactStore, BaseDocumentStore, BaseKnowledgeStore, BaseVectorStore
from framework.tools.base import BaseTool
from framework.tools.executor import ToolExecutor
from framework.tools.interfaces import ToolContext
from framework.tools.registry import ToolRegistry


class _EchoGateway(IChatModelGateway):
    def __init__(self) -> None:
        self.last_prompt: str | None = None
        self.last_metadata: dict[str, Any] | None = None

    def generate(self, prompt: str, *, metadata: dict[str, Any] | None = None) -> str:
        self.last_prompt = prompt
        self.last_metadata = metadata
        return f"generated::{prompt}"


def test_agent_specializations_preserve_base_lifecycle() -> None:
    gateway = _EchoGateway()
    context = AgentContext(task_id="task-1", node_name="writer", metadata={"correlation_id": "corr-1"})
    agent = ReviewAgent(name="reviewer", description="review draft", model_gateway=gateway)

    result = agent.invoke({"draft": "text"}, context)

    assert isinstance(agent, IAgent)
    assert agent.supports_tools() is False
    assert agent.supports_structured_output() is True
    assert isinstance(result, AgentResult)
    assert result.raw_output.startswith("generated::[reviewer]")
    assert result.metadata["agent"] == "reviewer"
    assert gateway.last_metadata == {"correlation_id": "corr-1"}


def test_agent_role_flags_and_human_gate_payload() -> None:
    gateway = _EchoGateway()
    context = AgentContext(task_id="task-2", node_name="gate")

    assert ToolAgent("tool", "tool agent", gateway).supports_tools() is True
    assert SupervisorAgent("supervisor", "routes", gateway).handle_result("next", context).raw_output == {
        "decision": "next"
    }

    human_result = HumanGateAgent("human", "gate", gateway).invoke({"reason": "approval"}, context)

    assert human_result.raw_output == {"status": "human_required", "input": {"reason": "approval"}}


class _ToolInput(BaseModel):
    value: int


class _ToolOutput(BaseModel):
    doubled: int
    actor: str


class _DoubleTool(BaseTool):
    def name(self) -> str:
        return "double"

    def description(self) -> str:
        return "Doubles an integer."

    def input_schema(self) -> type[BaseModel]:
        return _ToolInput

    def output_schema(self) -> type[BaseModel]:
        return _ToolOutput

    def _run(self, command: BaseModel, context: ToolContext) -> BaseModel | dict:
        validated = _ToolInput.model_validate(command)
        return {"doubled": validated.value * 2, "actor": context.actor}


def test_tool_registry_and_executor_validate_contracts() -> None:
    registry = ToolRegistry()
    tool = _DoubleTool()
    registry.register(tool)

    assert registry.has("double") is True
    assert list(registry.list_tools()) == ["double"]

    result = ToolExecutor(registry).execute(
        "double",
        _ToolInput(value=21),
        ToolContext(task_id="task-1", actor="unit-test"),
    )

    assert result == _ToolOutput(doubled=42, actor="unit-test")


def test_tool_base_validates_input_and_output() -> None:
    tool = _DoubleTool()

    with pytest.raises(ValueError):
        tool.execute({"value": "not-int"}, ToolContext(task_id="task-1", actor="unit-test"))  # type: ignore[arg-type]


class _MemoryRepository(BaseRepository):
    def __init__(self) -> None:
        self.payloads: dict[str, dict[str, Any]] = {}

    def get(self, entity_id: str) -> dict[str, Any] | None:
        return self.payloads.get(entity_id)

    def save(self, payload: dict[str, Any]) -> str:
        entity_id = str(payload["id"])
        self.payloads[entity_id] = payload
        return entity_id


def test_repository_factory_builds_registered_repository() -> None:
    factory = RepositoryFactory()
    factory.register("memory", _MemoryRepository)

    repo = factory.build("memory")
    entity_id = repo.save({"id": "doc-1", "title": "Doc"})

    assert entity_id == "doc-1"
    assert repo.get("doc-1") == {"id": "doc-1", "title": "Doc"}


def test_dummy_unit_of_work_tracks_commit_and_rollback_paths() -> None:
    with DummyUnitOfWork() as uow:
        assert uow is not None

    with pytest.raises(RuntimeError):
        with DummyUnitOfWork():
            raise RuntimeError("boom")


def test_base_repository_and_store_classes_are_explicit_abstract_stubs() -> None:
    with pytest.raises(NotImplementedError):
        BaseRepository().get("missing")
    with pytest.raises(NotImplementedError):
        BaseDocumentStore().read_document("doc-1")
    with pytest.raises(NotImplementedError):
        BaseKnowledgeStore().upsert_knowledge_block({"id": "block-1"})
    with pytest.raises(NotImplementedError):
        BaseVectorStore().upsert_vector("vec-1", [0.1], {})
    with pytest.raises(NotImplementedError):
        BaseArtifactStore().save_artifact("artifact-1", {})


def test_base_fastmcp_service_metadata_is_stable() -> None:
    service = BaseFastMcpService(service_name="contract-test", version="1.2.3")

    service.register_tools()

    assert service.metadata() == {"service_name": "contract-test", "version": "1.2.3"}
