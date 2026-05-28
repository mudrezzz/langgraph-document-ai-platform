# Release Go/No-Go Case

Mini-case to demonstrate file-based entry into the retrieval pipeline.

## Login

- `input/release_packet.md` - ​​realistic release package for the Payments v2 feature.

## What it demonstrates

1. Conversion of a markdown file into a retrieval dataset (`build_release_packet_dataset.py`).
2. Launch a retrieval task via the API with `case_dataset_path`.
3. Obtaining a meaningful artifact `release_readiness_report.md`:
- GO/NO-GO solution;
- blockers;
- unclosed approvals;
- evidence sources;
- summary of task events.

## Main demo script

- Sync demo Linux: `backend/scripts/demo_release_go_no_go_case.sh`
- Sync demo Windows: `backend/scripts/demo_release_go_no_go_case.ps1`
- Async demo Linux: `backend/scripts/demo_release_go_no_go_async_case.sh`

Async demo uses the same `release_packet.md`, but launches retrieval via `POST /api/v1/tasks/retrieval/start_async` and allows you to manually see the `queued -> completed` lifecycle on the same case.

## Output artifacts

- `output/release_packet_dataset.generated.json`
- `output/release_readiness_report.md`
- `output/release_readiness_report_async.md`

The `output/*.generated.json` and `output/*.md` files are considered runtime artifacts and are not committed to git.
