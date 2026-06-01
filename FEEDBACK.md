# Feedback Loop

This document defines how contributors can share structured feedback and project updates.

## 1. Why this exists

- keep contributor feedback visible and actionable;
- make progress updates easy to scan for maintainers and newcomers;
- preserve a public trail of what worked, what blocked progress, and what should be improved.

## 2. Where to post feedback

Use GitHub Issues with one of these labels:

- `community` for contributor-experience feedback;
- `documentation` for docs clarity and onboarding problems;
- `feature_request` for improvements to contributor flow or tooling.

For sensitive topics (security/privacy), follow `SECURITY.md` instead of public feedback threads.

## 3. What to include

Keep feedback concrete:

1. Context: which task/slice/PR you worked on.
2. What was smooth.
3. What was hard or confusing.
4. Suggested improvement (smallest practical change).
5. Optional: proposed owner or area (`docs`, `examples`, `ci`, `framework`).

## 4. Project update template

Use this template for periodic updates:

- [docs/project_update_template.md](docs/project_update_template.md)

You can post it:

- as an issue comment in the related task;
- as a short standalone issue labeled `community`;
- in a PR description when the update is tied to a specific change.

## 5. Review expectations

- maintainers triage feedback in the same queue as other community issues;
- feedback does not bypass quality/review rules;
- accepted improvements are tracked in `docs/DOCS_BACKLOG.md`.
