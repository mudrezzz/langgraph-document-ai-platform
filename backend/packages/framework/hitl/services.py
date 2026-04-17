from __future__ import annotations

from pydantic import BaseModel


class HumanInterruptService:
    """Формирует payload для interrupt-точки workflow."""

    def build_interrupt_payload(self, reason: str, data: dict) -> dict:
        return {"reason": reason, "data": data, "status": "interrupt"}


class HumanResumeService:
    """Валидирует и нормализует resume payload."""

    def parse_resume_payload(self, schema: type[BaseModel], payload: dict) -> BaseModel:
        return schema.model_validate(payload)


class ApprovalPolicy:
    """Политика обязательных шагов ручного подтверждения."""

    def __init__(self, required_points: set[str]) -> None:
        self._required_points = required_points

    def is_required(self, point_name: str) -> bool:
        return point_name in self._required_points
