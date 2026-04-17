from __future__ import annotations


class TaskNotFoundError(KeyError):
    """Задача не найдена в task registry."""


class InvalidTaskStateError(ValueError):
    """Состояние задачи не соответствует ожидаемому контракту."""