from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from application.async_dispatcher import AuthoringAsyncDispatcher, InlineAuthoringAsyncDispatcher
from application.authoring_service import AuthoringApplicationService
from application.artifact_service import ArtifactApplicationService
from application.document_service import DocumentApplicationService
from application.retrieval_service import RetrievalApplicationService
from application.task_service import TaskApplicationService
from schemas.api.contracts import StartAuthoringTaskRequest, SubmitHitlReviewRequest
from framework.models.interfaces import IChatModelGateway
from infra.celery import CeleryAuthoringAsyncDispatcher
from infra.openrouter import OpenRouterChatModelGateway
from infra.postgres.checkpoint_store import LangGraphPostgresCheckpointStore
from infra.postgres.config import PostgresSettings
from infra.postgres.artifact_store import PostgresArtifactStore
from infra.postgres.hitl_action_store import PostgresHitlActionStore
from infra.postgres.document_repository import PostgresDocumentRepository
from infra.postgres.task_artifact_registry import PostgresTaskArtifactRegistry
from infra.postgres.task_registry import PostgresTaskRegistry
from infra.vllm.chat_gateway import VllmChatModelGateway


@dataclass(slots=True)
class LlmRuntimeConfig:
    """Конфигурация подключения генеративной модели для authoring."""

    enabled: bool
    strict: bool
    provider: str
    model_name: str | None
    chat_gateway: IChatModelGateway | None


def _env_flag(name: str, default: bool = False) -> bool:
    """Нормализует bool-переменную окружения."""

    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    """Читает int-переменную окружения с безопасным fallback."""

    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _build_llm_runtime_config() -> LlmRuntimeConfig:
    """Собирает конфигурацию LLM runtime из env-переменных."""

    enabled = _env_flag("APP_LLM_ENABLED", default=False)
    strict = _env_flag("APP_LLM_STRICT", default=False)
    provider = os.getenv("APP_LLM_PROVIDER", "openrouter").strip().lower() or "openrouter"

    if not enabled:
        return LlmRuntimeConfig(
            enabled=False,
            strict=strict,
            provider="deterministic",
            model_name=None,
            chat_gateway=None,
        )

    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        model_name = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip() or "openai/gpt-4o-mini"

        if not api_key:
            if strict:
                raise ValueError("APP_LLM_STRICT=true требует OPENROUTER_API_KEY")
            return LlmRuntimeConfig(
                enabled=True,
                strict=strict,
                provider=provider,
                model_name=model_name,
                chat_gateway=None,
            )

        gateway = OpenRouterChatModelGateway(
            api_key=api_key,
            model_name=model_name,
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            timeout_sec=int(os.getenv("OPENROUTER_TIMEOUT_SEC", "60")),
            app_name=os.getenv("OPENROUTER_APP_NAME", "langgraph-document-ai-platform"),
            app_url=os.getenv("OPENROUTER_APP_URL", "http://localhost"),
        )
        return LlmRuntimeConfig(
            enabled=True,
            strict=strict,
            provider=provider,
            model_name=model_name,
            chat_gateway=gateway,
        )

    if provider == "vllm_mock":
        model_name = os.getenv("VLLM_MODEL_NAME", "mock-vllm-model").strip() or "mock-vllm-model"
        return LlmRuntimeConfig(
            enabled=True,
            strict=strict,
            provider=provider,
            model_name=model_name,
            chat_gateway=VllmChatModelGateway(model_name=model_name),
        )

    if strict:
        raise ValueError(f"Неподдерживаемый APP_LLM_PROVIDER: {provider}")
    return LlmRuntimeConfig(
        enabled=True,
        strict=strict,
        provider=provider,
        model_name=None,
        chat_gateway=None,
    )


def _build_authoring_dispatcher(
    *,
    authoring_service: AuthoringApplicationService,
) -> AuthoringAsyncDispatcher:
    """Собирает dispatcher запуска authoring в async режиме."""

    provider = os.getenv("APP_ASYNC_PROVIDER", "inline").strip().lower() or "inline"

    if provider == "celery":
        return CeleryAuthoringAsyncDispatcher(queue_name=os.getenv("APP_CELERY_QUEUE", "authoring"))
    if provider == "inline":
        return InlineAuthoringAsyncDispatcher(
            runner=lambda task_id, payload: authoring_service.run_existing_task(
                task_id=task_id,
                request=StartAuthoringTaskRequest.model_validate(payload),
            ),
            hitl_runner=lambda task_id, payload: authoring_service.process_hitl_action(
                task_id=task_id,
                request=SubmitHitlReviewRequest.model_validate(payload.get("request", {})),
                action_id=str(payload.get("action_id", "")),
            ),
        )

    raise ValueError(f"Неподдерживаемый APP_ASYNC_PROVIDER: {provider}")


class ApiContainer:
    """DI-контейнер API сервиса."""

    def __init__(self) -> None:
        settings = PostgresSettings.from_env()
        use_fallback = settings.allow_fallback_persistence
        checkpoint_store = LangGraphPostgresCheckpointStore.from_settings(
            settings,
            use_fallback_if_unset=use_fallback,
        )
        registry = PostgresTaskRegistry.from_settings(
            settings,
            use_fallback_if_unset=use_fallback,
        )
        document_repository = PostgresDocumentRepository.from_settings(
            settings,
            use_fallback_if_unset=use_fallback,
        )
        artifact_store = PostgresArtifactStore.from_settings(
            settings,
            use_fallback_if_unset=use_fallback,
        )
        task_artifact_registry = PostgresTaskArtifactRegistry.from_settings(
            settings,
            use_fallback_if_unset=use_fallback,
        )
        hitl_action_store = PostgresHitlActionStore.from_settings(
            settings,
            use_fallback_if_unset=use_fallback,
        )
        llm_runtime_config = _build_llm_runtime_config()
        task_service = TaskApplicationService(registry=registry, checkpoint_store=checkpoint_store)
        retrieval_service = RetrievalApplicationService(task_service=task_service)

        self.settings = settings
        self.task_service = task_service
        self.document_service = DocumentApplicationService(repository=document_repository)
        self.artifact_service = ArtifactApplicationService(artifact_store=artifact_store)
        self.retrieval_service = retrieval_service
        self.authoring_service = AuthoringApplicationService(
            task_service=task_service,
            retrieval_service=retrieval_service,
            artifact_service=self.artifact_service,
            task_artifact_registry=task_artifact_registry,
            hitl_action_store=hitl_action_store,
            chat_model_gateway=llm_runtime_config.chat_gateway,
            llm_enabled=llm_runtime_config.enabled,
            llm_strict_mode=llm_runtime_config.strict,
            llm_provider=llm_runtime_config.provider,
            llm_model_name=llm_runtime_config.model_name,
            hitl_max_iterations=_env_int("APP_HITL_MAX_ITERATIONS", 2),
            hitl_wait_timeout_sec=_env_int("APP_HITL_WAIT_TIMEOUT_SEC", 1800),
        )
        self.authoring_dispatcher = _build_authoring_dispatcher(authoring_service=self.authoring_service)


@lru_cache(maxsize=1)
def get_container() -> ApiContainer:
    """Возвращает singleton-контейнер API зависимостей."""

    return ApiContainer()
