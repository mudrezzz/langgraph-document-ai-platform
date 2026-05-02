"""Three focused BaseWorkflow subclasses for the device search agent.

Phase 1 — DevicePlanningWorkflow  (2 nodes):
    parse_intent → map_criteria

Phase 2 — DeviceResearchWorkflow  (4 nodes):
    search_listings → gather_evidence → enrich_reviews → score_and_compare

Phase 3 — DeviceReportWorkflow    (1 node):
    generate_report

All three share handler methods via _DeviceSearchHandlersMixin and operate
on the same DeviceSearchState, so state flows through unmodified.
"""
from __future__ import annotations

import json
import re
from typing import Any

from framework.models.interfaces import IChatModelGateway
from framework.workflows.base import (
    BaseWorkflow,
    WorkflowExecutionContext,
    WorkflowNodeEventSink,
    WorkflowNodeSpec,
)

from agent_examples.patterns.device_search.prompts import (
    ANALYZE_REVIEWS_PROMPT,
    EVALUATE_CRITERION_PROMPT,
    EXTRACT_LISTINGS_PROMPT,
    GENERATE_REPORT_PROMPT,
    MAP_CRITERIA_PROMPT,
    PARSE_INTENT_PROMPT,
)
from agent_examples.patterns.device_search.search_tools import (
    format_results_for_llm,
    search_device_benchmarks,
    search_marketplace_listings,
    search_user_reviews,
)
from agent_examples.patterns.device_search.state import (
    ConsumerCriterion,
    CriterionScore,
    DeviceListing,
    DeviceScore,
    DeviceSearchState,
    EvidenceItem,
    ReviewInsight,
)

# Maximum candidates to score in detail (keeps search + LLM calls bounded)
MAX_DEVICES_TO_SCORE = 4
# Top criteria by weight to gather external evidence for
MAX_EVIDENCE_CRITERIA = 4


# ── JSON extraction ───────────────────────────────────────────────────────────


def _extract_json(raw: str) -> Any:
    """Extract the leftmost JSON value (object or array) from an LLM response."""
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()

    obj_idx = cleaned.find("{")
    arr_idx = cleaned.find("[")

    if obj_idx == -1 and arr_idx == -1:
        return {}

    if arr_idx != -1 and (obj_idx == -1 or arr_idx <= obj_idx):
        start_char, end_char, idx = "[", "]", arr_idx
    else:
        start_char, end_char, idx = "{", "}", obj_idx

    depth = 0
    for pos, ch in enumerate(cleaned[idx:], idx):
        if ch == start_char:
            depth += 1
        elif ch == end_char:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(cleaned[idx : pos + 1])
                except json.JSONDecodeError:
                    break

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}


# ── State helpers ─────────────────────────────────────────────────────────────


def _trace(state: DeviceSearchState, node: str, data: dict) -> DeviceSearchState:
    return state.model_copy(
        update={"reasoning_trace": state.reasoning_trace + [{"node": node, **data}]}
    )


def _coerce_evidence_item(raw: Any) -> EvidenceItem:
    """Restore EvidenceItem from plain dict after LangGraph serialisation."""
    if isinstance(raw, EvidenceItem):
        return raw
    if isinstance(raw, dict):
        return EvidenceItem(
            source_url=str(raw.get("source_url", "")),
            title=str(raw.get("title", "")),
            snippet=str(raw.get("snippet", ""))[:300],
            evidence_type=raw.get("evidence_type", "unknown"),  # type: ignore[arg-type]
            confidence=float(raw.get("confidence", 0.5)),
        )
    return EvidenceItem(source_url="", title="", snippet=str(raw))


def _coerce_review_insight(raw: Any) -> ReviewInsight:
    if isinstance(raw, ReviewInsight):
        return raw
    if isinstance(raw, dict):
        evidence = [_coerce_evidence_item(e) for e in (raw.get("evidence") or [])]
        return ReviewInsight(
            criterion_name=str(raw.get("criterion_name", "")),
            sentiment=raw.get("sentiment", "neutral"),  # type: ignore[arg-type]
            insight=str(raw.get("insight", "")),
            evidence=evidence,
        )
    return ReviewInsight(criterion_name="", insight=str(raw))


# ── Shared handler mixin ──────────────────────────────────────────────────────


class _DeviceSearchHandlersMixin:
    """All seven node handler methods, shared across the three workflow classes."""

    _llm: IChatModelGateway

    # ── parse_intent ──────────────────────────────────────────────────────────

    def _parse_intent_node(
        self, state: DeviceSearchState, ctx: WorkflowExecutionContext
    ) -> DeviceSearchState:
        _ = ctx
        prompt = PARSE_INTENT_PROMPT.format(query=state.query)
        raw = self._llm.generate(prompt, metadata={"temperature": 0.1})
        parsed = _extract_json(raw)

        device_type = str(parsed.get("device_type") or "устройство")
        device_type_en = str(parsed.get("device_type_en") or "device")
        budget_rub = parsed.get("budget_rub")
        if isinstance(budget_rub, (int, float)):
            budget_rub = int(budget_rub)
        else:
            budget_rub = None
        use_cases = [str(u) for u in (parsed.get("use_cases") or [])]

        state = _trace(state, "parse_intent", {
            "device_type": device_type,
            "budget_rub": budget_rub,
            "use_cases": use_cases,
        })
        return state.model_copy(update={
            "device_type": device_type,
            "budget_rub": budget_rub,
            "use_cases": use_cases,
            "task_context": {
                **state.task_context,
                "_device_type_en": device_type_en,
                # preserve original query for report even if re-run with adjustments
                "_original_query": state.task_context.get("_original_query") or state.query,
            },
        })

    # ── map_criteria ──────────────────────────────────────────────────────────

    def _map_criteria_node(
        self, state: DeviceSearchState, ctx: WorkflowExecutionContext
    ) -> DeviceSearchState:
        _ = ctx
        budget_info = f"{state.budget_rub} руб." if state.budget_rub else "не указан"
        prompt = MAP_CRITERIA_PROMPT.format(
            device_type=state.device_type,
            use_cases=", ".join(state.use_cases),
            budget_info=budget_info,
        )
        raw = self._llm.generate(prompt, metadata={"temperature": 0.2})
        criteria_raw = _extract_json(raw)
        if not isinstance(criteria_raw, list):
            criteria_raw = []

        criteria = [
            ConsumerCriterion(
                name=str(c.get("name", "")),
                weight=float(c.get("weight", 0.2)),
                spec_thresholds={
                    str(k): str(v) for k, v in (c.get("spec_thresholds") or {}).items()
                },
                description=str(c.get("description", "")),
                measurability=c.get("measurability", "searchable"),  # type: ignore[arg-type]
            )
            for c in criteria_raw
            if c.get("name")
        ]

        total_weight = sum(c.weight for c in criteria) or 1.0
        criteria = [
            c.model_copy(update={"weight": c.weight / total_weight}) for c in criteria
        ]

        state = _trace(state, "map_criteria", {
            "criteria": [
                {
                    "name": c.name,
                    "weight": round(c.weight, 2),
                    "measurability": c.measurability,
                }
                for c in criteria
            ],
        })
        return state.model_copy(update={"consumer_criteria": criteria})

    # ── search_listings ───────────────────────────────────────────────────────

    def _search_listings_node(
        self, state: DeviceSearchState, ctx: WorkflowExecutionContext
    ) -> DeviceSearchState:
        _ = ctx
        device_type_en = str(state.task_context.get("_device_type_en", "device"))

        # Extract spec keywords from top searchable criteria to enrich search queries.
        # Criteria are already mapped by Phase 1 (HITL-1 runs before this node).
        searchable = [c for c in state.consumer_criteria if c.measurability == "searchable"]
        top2 = sorted(searchable, key=lambda c: c.weight, reverse=True)[:2]
        criteria_hints = [
            " ".join(list(c.spec_thresholds.keys())[:2])
            for c in top2
            if c.spec_thresholds
        ]

        raw_results, queries_used = search_marketplace_listings(
            device_type_en=device_type_en,
            device_type_ru=state.device_type,
            budget_rub=state.budget_rub,
            criteria_hints=criteria_hints,
        )

        budget_info = f"{state.budget_rub} руб." if state.budget_rub else "не указан"
        prompt = EXTRACT_LISTINGS_PROMPT.format(
            device_type=state.device_type,
            budget_info=budget_info,
            search_results=format_results_for_llm(raw_results, max_chars=8000),
        )
        raw = self._llm.generate(prompt, metadata={"temperature": 0.1, "max_tokens": 1500})
        listings_raw = _extract_json(raw)
        if not isinstance(listings_raw, list):
            listings_raw = []

        listings = [
            DeviceListing(
                name=str(l.get("name", "")),
                price_rub=int(l["price_rub"]) if isinstance(l.get("price_rub"), (int, float)) else None,
                marketplace=str(l.get("marketplace", "")),
                url=str(l.get("url", "")),
                raw_specs={str(k): str(v) for k, v in (l.get("raw_specs") or {}).items()},
            )
            for l in listings_raw
            if l.get("name")
        ]

        will_score = listings[:MAX_DEVICES_TO_SCORE]
        excluded = listings[MAX_DEVICES_TO_SCORE:]

        state = _trace(state, "search_listings", {
            "queries_used": queries_used,
            "raw_results_count": len(raw_results),
            "found": [{"name": l.name, "price_rub": l.price_rub} for l in listings],
            "will_score": [l.name for l in will_score],
            "excluded_from_scoring": [
                {"name": l.name, "reason": f"позиция > {MAX_DEVICES_TO_SCORE} в результатах"}
                for l in excluded
            ],
        })
        return state.model_copy(update={"listings": listings})

    # ── gather_evidence ───────────────────────────────────────────────────────

    def _gather_evidence_node(
        self, state: DeviceSearchState, ctx: WorkflowExecutionContext
    ) -> DeviceSearchState:
        _ = ctx
        candidates = state.listings[:MAX_DEVICES_TO_SCORE]

        # Only gather evidence for searchable criteria, sorted by weight
        searchable_criteria = [
            c for c in state.consumer_criteria if c.measurability == "searchable"
        ]
        top_criteria = sorted(searchable_criteria, key=lambda c: c.weight, reverse=True)[
            :MAX_EVIDENCE_CRITERIA
        ]
        skipped_criteria = [
            c.name for c in state.consumer_criteria if c.measurability == "inferred"
        ]

        evidence_map: dict[str, dict[str, list[EvidenceItem]]] = {}

        for device in candidates:
            evidence_map[device.name] = {}
            for criterion in top_criteria:
                search_hint = f"{criterion.name} {' '.join(criterion.spec_thresholds.keys())}".strip()
                raw_results = search_device_benchmarks(device.name, search_hint)
                evidence_map[device.name][criterion.name] = [
                    EvidenceItem(
                        source_url=r.get("url", ""),
                        title=r.get("title", ""),
                        snippet=r.get("snippet", "")[:300],
                        evidence_type=_classify_source(r.get("url", "")),
                        confidence=0.7,
                    )
                    for r in raw_results[:5]
                ]

        state = _trace(state, "gather_evidence", {
            "devices_searched": [d.name for d in candidates],
            "criteria_searched": [c.name for c in top_criteria],
            "criteria_skipped_inferred": skipped_criteria,
            "evidence_items_total": sum(
                len(ev) for dev_ev in evidence_map.values() for ev in dev_ev.values()
            ),
        })
        return state.model_copy(
            update={"task_context": {**state.task_context, "_evidence_map": evidence_map}}
        )

    # ── enrich_reviews ────────────────────────────────────────────────────────

    def _enrich_reviews_node(
        self, state: DeviceSearchState, ctx: WorkflowExecutionContext
    ) -> DeviceSearchState:
        _ = ctx
        candidates = state.listings[:MAX_DEVICES_TO_SCORE]
        criteria_names = [c.name for c in state.consumer_criteria]

        review_map: dict[str, list[ReviewInsight]] = {}

        for device in candidates:
            raw_results = search_user_reviews(device.name)
            if not raw_results:
                review_map[device.name] = []
                continue

            prompt = ANALYZE_REVIEWS_PROMPT.format(
                device_name=device.name,
                criteria_names=", ".join(criteria_names),
                review_snippets=format_results_for_llm(raw_results, max_chars=3000),
            )
            raw = self._llm.generate(prompt, metadata={"temperature": 0.2, "max_tokens": 1000})
            review_data = _extract_json(raw)
            if not isinstance(review_data, list):
                review_data = []

            insights: list[ReviewInsight] = []
            for item in review_data:
                criterion_name = str(item.get("criterion_name", ""))
                if criterion_name not in criteria_names:
                    continue
                source_url = str(item.get("source_url", ""))
                source_snippet = str(item.get("source_snippet", ""))
                evidence = (
                    [EvidenceItem(
                        source_url=source_url,
                        title=device.name + " отзыв",
                        snippet=source_snippet[:200],
                        evidence_type="user_review",
                        confidence=0.6,
                    )]
                    if source_snippet
                    else []
                )
                insights.append(ReviewInsight(
                    criterion_name=criterion_name,
                    sentiment=str(item.get("sentiment", "neutral")),  # type: ignore[arg-type]
                    insight=str(item.get("insight", "")),
                    evidence=evidence,
                ))
            review_map[device.name] = insights

        state = _trace(state, "enrich_reviews", {
            "devices": {k: len(v) for k, v in review_map.items()},
        })
        return state.model_copy(
            update={"task_context": {**state.task_context, "_review_map": review_map}}
        )

    # ── score_and_compare ─────────────────────────────────────────────────────

    def _score_and_compare_node(
        self, state: DeviceSearchState, ctx: WorkflowExecutionContext
    ) -> DeviceSearchState:
        _ = ctx
        evidence_map: dict[str, dict[str, list]] = state.task_context.get("_evidence_map", {})
        review_map: dict[str, list] = state.task_context.get("_review_map", {})

        searchable_criteria = [
            c for c in state.consumer_criteria if c.measurability == "searchable"
        ]
        top_criteria = sorted(searchable_criteria, key=lambda c: c.weight, reverse=True)[
            :MAX_EVIDENCE_CRITERIA
        ]

        device_scores: list[DeviceScore] = []
        all_gaps: list[str] = []

        for device in state.listings[:MAX_DEVICES_TO_SCORE]:
            criterion_scores: list[CriterionScore] = []
            device_evidence = evidence_map.get(device.name, {})

            for criterion in top_criteria:
                evidence_items = [
                    _coerce_evidence_item(e)
                    for e in device_evidence.get(criterion.name, [])
                ]
                evidence_snippets = format_results_for_llm(
                    [{"title": e.title, "url": e.source_url, "snippet": e.snippet}
                     for e in evidence_items],
                    max_chars=2500,
                )
                prompt = EVALUATE_CRITERION_PROMPT.format(
                    device_name=device.name,
                    criterion_name=criterion.name,
                    thresholds=json.dumps(criterion.spec_thresholds, ensure_ascii=False),
                    criterion_description=criterion.description,
                    raw_specs=json.dumps(device.raw_specs, ensure_ascii=False),
                    evidence_snippets=evidence_snippets,
                )
                raw = self._llm.generate(
                    prompt, metadata={"temperature": 0.1, "max_tokens": 800}
                )
                eval_data = _extract_json(raw)
                if not isinstance(eval_data, dict):
                    eval_data = {}

                scored_evidence = [
                    EvidenceItem(
                        source_url=str(e.get("source_url", "")),
                        title=str(e.get("title", "")),
                        snippet=str(e.get("snippet", ""))[:250],
                        evidence_type=str(e.get("evidence_type", "unknown")),  # type: ignore[arg-type]
                        confidence=float(e.get("confidence", 0.5)),
                    )
                    for e in (eval_data.get("evidence_used") or [])
                ]
                gaps = [str(g) for g in (eval_data.get("unresolved_gaps") or [])]
                all_gaps.extend(gaps)

                criterion_scores.append(CriterionScore(
                    criterion_name=criterion.name,
                    score=float(eval_data.get("score", 0.5)),
                    assessment=str(eval_data.get("assessment", "")),
                    evidence=scored_evidence,
                    unresolved_gaps=gaps,
                ))

            total = sum(
                cs.score * next(
                    (c.weight for c in top_criteria if c.name == cs.criterion_name), 0.25
                )
                for cs in criterion_scores
            )

            raw_insights = review_map.get(device.name, [])
            review_insights = [_coerce_review_insight(r) for r in raw_insights]

            device_scores.append(DeviceScore(
                device=device,
                criterion_scores=criterion_scores,
                total_score=round(total, 3),
                summary="",
                review_insights=review_insights,
            ))

        device_scores.sort(key=lambda ds: ds.total_score, reverse=True)

        all_confidences = [
            e.confidence
            for ds in device_scores[:2]
            for cs in ds.criterion_scores
            for e in cs.evidence
        ]
        overall_confidence = (
            sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        )

        # Deduplicate gaps preserving order (set() loses order on older Pythons)
        seen_gaps: set[str] = set()
        unique_gaps: list[str] = []
        for g in all_gaps:
            if g not in seen_gaps:
                seen_gaps.add(g)
                unique_gaps.append(g)

        state = _trace(state, "score_and_compare", {
            "ranking": [
                {"device": ds.device.name, "total_score": ds.total_score}
                for ds in device_scores
            ],
        })
        return state.model_copy(update={
            "device_scores": device_scores,
            "confidence": round(overall_confidence, 3),
            "unresolved_gaps": unique_gaps,
        })

    # ── generate_report ───────────────────────────────────────────────────────

    def _generate_report_node(
        self, state: DeviceSearchState, ctx: WorkflowExecutionContext
    ) -> DeviceSearchState:
        _ = ctx
        budget_info = f"{state.budget_rub} руб." if state.budget_rub else "не указан"
        original_query = state.task_context.get("_original_query") or state.query

        hitl_context = ""
        if state.hitl.criteria_adjustments:
            hitl_context += f"\nПользователь скорректировал критерии: {state.hitl.criteria_adjustments}"
        if state.hitl.results_adjustments:
            hitl_context += f"\nПользователь прокомментировал результаты: {state.hitl.results_adjustments}"

        criteria_summary = "\n".join(
            f"- {c.name} (вес {round(c.weight * 100)}%"
            + (", не измеряется поиском" if c.measurability == "inferred" else "")
            + f"): {c.description}"
            for c in state.consumer_criteria
        )

        devices_summary = _format_devices_for_report(state.device_scores)

        trace_summary = json.dumps(
            [{"шаг": t["node"], **{k: v for k, v in t.items() if k != "node"}}
             for t in state.reasoning_trace],
            ensure_ascii=False, indent=2,
        )

        prompt = GENERATE_REPORT_PROMPT.format(
            device_type=state.device_type,
            original_query=original_query,
            use_cases=", ".join(state.use_cases),
            budget_info=budget_info,
            hitl_context=hitl_context,
            criteria_summary=criteria_summary,
            devices_summary=devices_summary,
            reasoning_trace=trace_summary,
        )
        report = self._llm.generate(prompt, metadata={"temperature": 0.3, "max_tokens": 2500})

        state = _trace(state, "generate_report", {"report_length": len(report)})
        return state.model_copy(update={"final_report": report})


# ── Three workflow classes ────────────────────────────────────────────────────


class DevicePlanningWorkflow(_DeviceSearchHandlersMixin, BaseWorkflow):
    """Phase 1: parse user intent and map to weighted consumer criteria (2 nodes)."""

    def __init__(
        self,
        llm: IChatModelGateway,
        event_sink: WorkflowNodeEventSink | None = None,
    ) -> None:
        self._llm = llm
        BaseWorkflow.__init__(self, use_langgraph_runtime=True, node_event_sink=event_sink)
        self.compile()

    def state_schema(self) -> type[DeviceSearchState]:
        return DeviceSearchState

    def workflow_nodes(self, *, is_resume: bool) -> list[WorkflowNodeSpec]:
        return [
            WorkflowNodeSpec("parse_intent", self._parse_intent_node),
            WorkflowNodeSpec("map_criteria", self._map_criteria_node),
        ]


class DeviceResearchWorkflow(_DeviceSearchHandlersMixin, BaseWorkflow):
    """Phase 2: search marketplaces, gather evidence, enrich reviews, score (4 nodes)."""

    def __init__(
        self,
        llm: IChatModelGateway,
        event_sink: WorkflowNodeEventSink | None = None,
    ) -> None:
        self._llm = llm
        BaseWorkflow.__init__(self, use_langgraph_runtime=True, node_event_sink=event_sink)
        self.compile()

    def state_schema(self) -> type[DeviceSearchState]:
        return DeviceSearchState

    def workflow_nodes(self, *, is_resume: bool) -> list[WorkflowNodeSpec]:
        return [
            WorkflowNodeSpec("search_listings", self._search_listings_node),
            WorkflowNodeSpec("gather_evidence", self._gather_evidence_node),
            WorkflowNodeSpec("enrich_reviews", self._enrich_reviews_node),
            WorkflowNodeSpec("score_and_compare", self._score_and_compare_node),
        ]


class DeviceReportWorkflow(_DeviceSearchHandlersMixin, BaseWorkflow):
    """Phase 3: generate final Markdown report (1 node)."""

    def __init__(
        self,
        llm: IChatModelGateway,
        event_sink: WorkflowNodeEventSink | None = None,
    ) -> None:
        self._llm = llm
        BaseWorkflow.__init__(self, use_langgraph_runtime=True, node_event_sink=event_sink)
        self.compile()

    def state_schema(self) -> type[DeviceSearchState]:
        return DeviceSearchState

    def workflow_nodes(self, *, is_resume: bool) -> list[WorkflowNodeSpec]:
        return [
            WorkflowNodeSpec("generate_report", self._generate_report_node),
        ]


# ── Report formatting helpers ─────────────────────────────────────────────────


def _classify_source(url: str) -> str:
    url_lower = url.lower()
    if any(d in url_lower for d in ("gsmarena", "notebookcheck", "rtings", "displayspecifications")):
        return "benchmark"
    if any(d in url_lower for d in ("expert", "ixbt", "3dnews", "arstechnica", "theverge")):
        return "expert_review"
    if any(d in url_lower for d in ("otzovik", "irecommend", "market.yandex", "ozon.ru/review")):
        return "user_review"
    return "expert_review"


def _format_devices_for_report(device_scores: list[DeviceScore]) -> str:
    lines: list[str] = []
    for ds in device_scores:
        lines.append(f"\n### {ds.device.name}")
        lines.append(f"Цена: {ds.device.price_rub} руб. | Итог: {round(ds.total_score * 10, 1)}/10")
        for cs in ds.criterion_scores:
            score_pct = round(cs.score * 100)
            evidence_urls = ", ".join(e.source_url for e in cs.evidence[:3] if e.source_url)
            lines.append(
                f"  {cs.criterion_name}: {score_pct}% — {cs.assessment}"
                + (f" [источники: {evidence_urls}]" if evidence_urls else "")
            )
        if ds.review_insights:
            lines.append("  Отзывы покупателей:")
            for ri in ds.review_insights[:3]:
                mark = "+" if ri.sentiment == "positive" else ("-" if ri.sentiment == "negative" else "~")
                lines.append(f"    [{mark}] {ri.insight} (критерий: {ri.criterion_name})")
        if ds.device.url:
            lines.append(f"  Ссылка: {ds.device.url}")
    return "\n".join(lines)
