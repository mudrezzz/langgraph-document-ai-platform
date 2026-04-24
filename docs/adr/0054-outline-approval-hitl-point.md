# ADR-0054: Outline approval HITL point

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

К этому этапу `Increment 28` уже имел typed `SectionContract`, section-level traceability, template-aware assembly и artifact export, но HITL по-прежнему включался только после section authoring / draft generation. В backlog инкремента изначально был заложен отдельный `outline approval` point, чтобы reviewer мог остановить pipeline раньше, до генерации секционных артефактов.

## Решение

1. При `hitl_required=true` и `workflow_mode=multi_step` переводить authoring task в `waiting_human` после построения outline/section contracts, но до section authoring.
2. Хранить в state `hitl_phase=outline_review` и `outline_snapshot` в `task_context`.
3. Расширить HITL read-model ответ полями:
   - `phase`;
   - `outline` (`template_id`, sections, objectives, required keywords, source refs).
4. При `approve` продолжать обычный pipeline: section authoring -> final review -> assembly/export.
5. При `needs_changes` на outline phase не запускать rewrite, а возвращать задачу обратно в `waiting_human` с обновленным pending reason.
6. Публичные endpoints не менять.

## Последствия

Плюсы:

- reviewer может остановить authoring раньше и увидеть план документа до генерации секций;
- future section workflows и reviewer UI проще строить поверх уже typed outline snapshot;
- expensive steps с section generation не запускаются до outline approval.

Минусы:

- `needs_changes` на outline phase пока не пересчитывает outline автоматически и требует внешнего rerun/input change;
- текущий HITL flow стал двухфазным (`outline_review` -> `final_review`) только на уровне state/read-model, без отдельного UI.
