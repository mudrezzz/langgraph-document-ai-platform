"""Pydantic state contracts for the device search agent."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ConsumerCriterion(BaseModel):
    """One consumer-facing quality dimension derived from use-case intent."""

    name: str
    weight: float  # 0.0 – 1.0, all criteria sum to ~1.0
    spec_thresholds: dict[str, str] = Field(default_factory=dict)
    description: str = ""
    # searchable = can be verified via web search/benchmarks
    # inferred   = can only be reasoned about, not directly measured
    measurability: Literal["searchable", "inferred"] = "searchable"


class DeviceListing(BaseModel):
    """Normalised device listing scraped from a marketplace."""

    name: str
    price_rub: int | None = None
    marketplace: str = ""
    url: str = ""
    raw_specs: dict[str, str] = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    """One traceable evidence snippet backing a score or insight."""

    source_url: str
    title: str
    snippet: str
    evidence_type: Literal[
        "benchmark", "expert_review", "official_specs", "user_review", "unknown"
    ] = "unknown"
    confidence: float = 0.5


class CriterionScore(BaseModel):
    """Score for a single device on a single consumer criterion, with full evidence."""

    criterion_name: str
    score: float  # 0.0 – 1.0
    assessment: str  # one-sentence human-readable verdict
    evidence: list[EvidenceItem] = Field(default_factory=list)
    unresolved_gaps: list[str] = Field(default_factory=list)


class ReviewInsight(BaseModel):
    """Real-world usage insight extracted from user reviews, mapped to a criterion."""

    criterion_name: str
    sentiment: Literal["positive", "negative", "neutral"] = "neutral"
    insight: str
    evidence: list[EvidenceItem] = Field(default_factory=list)


class DeviceScore(BaseModel):
    """Aggregated score for one device across all criteria."""

    device: DeviceListing
    criterion_scores: list[CriterionScore] = Field(default_factory=list)
    total_score: float = 0.0
    summary: str = ""
    review_insights: list[ReviewInsight] = Field(default_factory=list)


class HITLState(BaseModel):
    # Gate 1: criteria approval (after map_criteria, before search)
    criteria_phase: Literal["pending", "approved", "adjusted"] = "pending"
    criteria_feedback: str = ""
    criteria_adjustments: str = ""

    # Gate 2: results approval (after score_and_compare, before report)
    results_phase: Literal["pending", "approved", "adjusted"] = "pending"
    results_feedback: str = ""
    results_adjustments: str = ""


class DeviceSearchState(BaseModel):
    """Full mutable state threaded through every workflow node."""

    task_context: dict = Field(default_factory=dict)

    # Input (original_query preserved across criteria re-runs)
    query: str

    # After parse_intent
    device_type: str = ""
    budget_rub: int | None = None
    use_cases: list[str] = Field(default_factory=list)

    # After map_criteria
    consumer_criteria: list[ConsumerCriterion] = Field(default_factory=list)

    # After search_listings
    listings: list[DeviceListing] = Field(default_factory=list)

    # After gather_evidence + enrich_reviews + score_and_compare
    device_scores: list[DeviceScore] = Field(default_factory=list)

    # HITL gates
    hitl: HITLState = Field(default_factory=HITLState)

    # After generate_report
    final_report: str | None = None

    # Observability
    reasoning_trace: list[dict] = Field(default_factory=list)
    unresolved_gaps: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    error_message: str | None = None
