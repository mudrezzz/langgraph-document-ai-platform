# ADR-0034: Binary demo documents for Knowledge Factory acceptance

Date: 2026-04-23

Status: Accepted

## Context

ADR-0031 added a parser boundary for `.docx` and `.pdf`, but the main release go/no-go multifile demo actually only contained `.md/.txt/.json`. Because of this, the manual acceptance run did not confirm support for binary document formats, although the framework already had the appropriate adapters.

## Solution

1. Expand `release_go_no_go_multifile_case/input` with two input documents:
   - `05_release_notes.docx`;
   - `06_audit_summary.pdf`.
2. Add generator `backend/scripts/build_binary_demo_documents.py` and shell/PowerShell wrappers.
3. Add the `--build-binary-demo-docs` flag to canonical indexing/retrieval smoke scripts.
4. Update the manual PostgreSQL runbook so that the manual acceptance run checks `.md/.txt/.json/.docx/.pdf`.

## Consequences

- Demo now actually validates all formats of the current parser boundary.
- Smoke Knowledge Indexing expects 6 canonical documents and file types `docx/json/md/pdf/txt`.
- PDF fixture can give quality flag `low_text_density`; This is the expected behavior of MVP parser quality gates.
- Binary fixtures remain small and are versioned along with the demo, and a generator is needed to restore/rewrite fixture files.
