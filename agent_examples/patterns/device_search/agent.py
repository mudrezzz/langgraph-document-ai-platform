"""DeviceSearchAgent — three-phase orchestrator with two HITL gates.

Flow:
    Phase 1  DevicePlanningWorkflow   parse_intent → map_criteria
    HITL-1   Criteria approval gate   show criteria, allow adjustments + re-run
    Phase 2  DeviceResearchWorkflow   search → evidence → reviews → score
    HITL-2   Results approval gate    show ranking, allow comments
    Phase 3  DeviceReportWorkflow     generate_report
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from infra.openrouter.chat_gateway import OpenRouterChatModelGateway

from agent_examples.patterns.device_search.config import DeviceSearchConfig
from agent_examples.patterns.device_search.event_sink import DeviceSearchEventSink
from agent_examples.patterns.device_search.state import DeviceSearchState, HITLState
from agent_examples.patterns.device_search.workflow import (
    DevicePlanningWorkflow,
    DeviceResearchWorkflow,
    DeviceReportWorkflow,
)


@dataclass
class DeviceSearchAgent:
    config: DeviceSearchConfig

    def run(self, query: str, non_interactive: bool = False) -> dict[str, Any]:
        llm = OpenRouterChatModelGateway(
            api_key=self.config.openrouter_api_key,
            model_name=self.config.openrouter_model,
            base_url=self.config.openrouter_base_url,
        )

        # One shared sink collects events from all three workflow phases
        sink = DeviceSearchEventSink(verbose=True)

        planning_wf = DevicePlanningWorkflow(llm=llm, event_sink=sink)
        research_wf = DeviceResearchWorkflow(llm=llm, event_sink=sink)
        report_wf = DeviceReportWorkflow(llm=llm, event_sink=sink)

        initial = DeviceSearchState(
            query=query,
            task_context={"requester": self.config.requester},
        )

        # ── Phase 1: parse intent + map criteria ──────────────────────────────
        print("\n[Phase 1] Анализ запроса и формирование критериев…", flush=True)
        state = planning_wf.invoke(initial)

        # ── HITL-1: criteria gate (with optional re-run) ──────────────────────
        state = self._hitl_criteria_gate(
            state, planning_wf, non_interactive=non_interactive
        )

        # ── Phase 2: search + evidence + score ────────────────────────────────
        print("\n[Phase 2] Поиск устройств и сбор доказательств…", flush=True)
        state = research_wf.invoke(state)

        # ── HITL-2: results gate ──────────────────────────────────────────────
        state = self._hitl_results_gate(state, non_interactive=non_interactive)

        # ── Phase 3: generate report ──────────────────────────────────────────
        print("\n[Phase 3] Составление отчёта…", flush=True)
        state = report_wf.invoke(state)

        # Print timeline to stdout for immediate human inspection
        sink.print_timeline()

        return self._build_result(state, sink)

    # ── HITL Gate 1: criteria approval ────────────────────────────────────────

    def _hitl_criteria_gate(
        self,
        state: DeviceSearchState,
        planning_wf: DevicePlanningWorkflow,
        *,
        non_interactive: bool,
    ) -> DeviceSearchState:
        print("\n" + "=" * 68)
        print("HITL GATE 1 — Согласование критериев выбора")
        print("=" * 68)
        print(f"\n  Устройство : {state.device_type}")
        print(f"  Бюджет     : {state.budget_rub or 'не указан'} руб.")
        print(f"  Цели       : {', '.join(state.use_cases)}")
        print("\n  Сформированные критерии:")
        for c in state.consumer_criteria:
            measurability_mark = "" if c.measurability == "searchable" else " [не измеряется поиском]"
            print(
                f"    [{round(c.weight * 100):>2}%] {c.name}{measurability_mark}"
                + (f" — {c.description}" if c.description else "")
            )
            if c.spec_thresholds:
                th = ", ".join(f"{k}: {v}" for k, v in c.spec_thresholds.items())
                print(f"         Пороги: {th}")
        print()
        print("-" * 68)

        if non_interactive:
            print("[non-interactive] Критерии приняты автоматически.")
            return state.model_copy(
                update={"hitl": HITLState(criteria_phase="approved")}
            )

        print(
            "Введите 'да' для подтверждения,\n"
            "или опишите корректировку (например: 'добавь поддержку стилуса'):"
        )
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            user_input = "да"

        if not user_input or user_input.lower() in {"да", "yes", "y", "+", "ок", "ok"}:
            return state.model_copy(
                update={"hitl": HITLState(criteria_phase="approved")}
            )

        # User requested adjustment — re-run planning with enriched query
        print(f"\n[HITL-1] Пересчитываю критерии с учётом: «{user_input}»")
        original_query = state.task_context.get("_original_query") or state.query
        adjusted_state = DeviceSearchState(
            query=original_query + "\nДополнительные требования к критериям: " + user_input,
            task_context={
                **state.task_context,
                "_original_query": original_query,
            },
        )
        state = planning_wf.invoke(adjusted_state)
        return state.model_copy(
            update={
                "hitl": HITLState(
                    criteria_phase="adjusted",
                    criteria_feedback=user_input,
                    criteria_adjustments=user_input,
                ),
                "query": original_query,  # restore original for report
            }
        )

    # ── HITL Gate 2: results approval ─────────────────────────────────────────

    def _hitl_results_gate(
        self, state: DeviceSearchState, *, non_interactive: bool
    ) -> DeviceSearchState:
        # Build a threshold lookup so we can show "требуется X, найдено Y"
        thresholds: dict[str, dict[str, str]] = {
            c.name: c.spec_thresholds for c in state.consumer_criteria
        }

        print("\n" + "=" * 68)
        print("HITL GATE 2 — Согласование результатов")
        print("=" * 68)
        print("\n  Предварительный рейтинг:")
        for i, ds in enumerate(state.device_scores[:4], 1):
            price = f"{ds.device.price_rub} руб." if ds.device.price_rub else "цена н/д"
            print(f"\n  {i}. {ds.device.name} — {round(ds.total_score * 10, 1)}/10  ({price})")

            # Key raw specs on the same line for quick sanity check
            if ds.device.raw_specs:
                specs_line = "  |  ".join(
                    f"{k}: {v}" for k, v in list(ds.device.raw_specs.items())[:4]
                )
                print(f"     Характеристики: {specs_line}")

            for cs in ds.criterion_scores:
                mark = "✓" if cs.score >= 0.7 else ("~" if cs.score >= 0.5 else "✗")
                score_str = f"{round(cs.score * 10, 1)}/10"

                # Show thresholds required so user can verify themselves
                th = thresholds.get(cs.criterion_name, {})
                th_str = (
                    "  [требуется: " + ", ".join(f"{k} {v}" for k, v in th.items()) + "]"
                    if th else ""
                )
                print(f"     {mark} {cs.criterion_name}: {score_str}{th_str}")

                # The assessment already contains the actual measured values from LLM
                if cs.assessment:
                    print(f"       → {cs.assessment}")

                # Show top evidence source so user can click and verify
                top_ev = next((e for e in cs.evidence if e.source_url), None)
                if top_ev:
                    print(f"       источник: {top_ev.source_url}")

        if state.unresolved_gaps:
            print(f"\n  Не удалось проверить ({len(state.unresolved_gaps)} пункт(ов)):")
            for g in state.unresolved_gaps[:3]:
                print(f"    · {g}")
        print()
        print("-" * 68)

        if non_interactive:
            print("[non-interactive] Результаты приняты автоматически.")
            return state.model_copy(
                update={
                    "hitl": state.hitl.model_copy(
                        update={"results_phase": "approved"}
                    )
                }
            )

        print(
            "Введите 'да' для перехода к отчёту,\n"
            "или оставьте комментарий (он будет учтён в отчёте):"
        )
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            user_input = "да"

        if not user_input or user_input.lower() in {"да", "yes", "y", "+", "ок", "ok"}:
            return state.model_copy(
                update={
                    "hitl": state.hitl.model_copy(
                        update={"results_phase": "approved"}
                    )
                }
            )

        return state.model_copy(
            update={
                "hitl": state.hitl.model_copy(
                    update={
                        "results_phase": "adjusted",
                        "results_feedback": user_input,
                        "results_adjustments": user_input,
                    }
                )
            }
        )

    # ── Result serialisation ──────────────────────────────────────────────────

    def _build_result(
        self, state: DeviceSearchState, sink: DeviceSearchEventSink
    ) -> dict[str, Any]:
        return {
            "pattern": "device_search",
            "execution_model": "in_process_framework_workflow",
            "query": state.task_context.get("_original_query") or state.query,
            "device_type": state.device_type,
            "budget_rub": state.budget_rub,
            "use_cases": state.use_cases,
            "criteria": [
                {
                    "name": c.name,
                    "weight": round(c.weight, 2),
                    "measurability": c.measurability,
                }
                for c in state.consumer_criteria
            ],
            "ranking": [
                {
                    "rank": i,
                    "device": ds.device.name,
                    "price_rub": ds.device.price_rub,
                    "total_score": round(ds.total_score * 10, 1),
                    "criterion_scores": [
                        {
                            "criterion": cs.criterion_name,
                            "score": round(cs.score * 10, 1),
                            "assessment": cs.assessment,
                            "evidence_count": len(cs.evidence),
                            "unresolved_gaps": cs.unresolved_gaps,
                        }
                        for cs in ds.criterion_scores
                    ],
                    "review_insights": [
                        {
                            "criterion": ri.criterion_name,
                            "sentiment": ri.sentiment,
                            "insight": ri.insight,
                        }
                        for ri in ds.review_insights
                    ],
                    "marketplace_url": ds.device.url,
                }
                for i, ds in enumerate(state.device_scores, 1)
            ],
            "hitl": {
                "criteria_gate": state.hitl.criteria_phase,
                "criteria_adjustments": state.hitl.criteria_adjustments or None,
                "results_gate": state.hitl.results_phase,
                "results_adjustments": state.hitl.results_adjustments or None,
            },
            "confidence": state.confidence,
            "unresolved_gaps": state.unresolved_gaps,
            "reasoning_trace": state.reasoning_trace,
            # Node-level execution timeline from WorkflowNodeEventSink
            "node_timeline": sink.get_completed_nodes(),
            "node_failures": sink.get_failed_nodes(),
            "total_node_duration_ms": sink.total_duration_ms(),
            "final_report": state.final_report,
        }
