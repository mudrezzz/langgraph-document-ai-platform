from __future__ import annotations


class TaskNotFoundError(KeyError):
    """Задача не найдена в task registry."""


class InvalidTaskStateError(ValueError):
    """Состояние задачи не соответствует ожидаемому контракту."""


class WorkflowExecutionError(RuntimeError):
    """Ошибка исполнения workflow на application-уровне."""


class InvalidCursorError(ValueError):
    """Некорректный курсор пагинации истории задач."""
