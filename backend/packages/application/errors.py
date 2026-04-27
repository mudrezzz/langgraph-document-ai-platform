from __future__ import annotations


class TaskNotFoundError(KeyError):
    """Задача не найдена в task registry."""


class InvalidTaskStateError(ValueError):
    """Состояние задачи не соответствует ожидаемому контракту."""


class WorkflowExecutionError(RuntimeError):
    """Ошибка исполнения workflow на application-уровне."""


class InvalidCursorError(ValueError):
    """Некорректный курсор пагинации истории задач."""


class DocumentNotFoundError(KeyError):
    """Документ не найден в document repository."""


class ArtifactNotFoundError(KeyError):
    """Артефакт не найден в artifact store."""


class TaskArtifactLinkNotFoundError(KeyError):
    """Связь task -> artifact не найдена."""


class TemplateNotFoundError(KeyError):
    """Шаблон не найден в template library."""


class InvalidTemplateStatusTransitionError(ValueError):
    """Некорректный переход статуса шаблона."""


class ConfigurationNotFoundError(KeyError):
    """Конфигурация не найдена в configuration library."""
