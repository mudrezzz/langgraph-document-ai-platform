# Release Go/No-Go Multi-File Case

Mini-case for checking retrieval in a directory of several files.

## Input documents

- `input/01_scope_and_decision.md`
- `input/02_security_findings.md`
- `input/03_ops_readiness.txt`
- `input/04_approvals.json`
- `input/05_release_notes.docx`
- `input/06_audit_summary.pdf`
- `input/07_scanned_signoff.pdf`
- `input/08_release_tracker.xlsx`
- `input/09_release_briefing.pptx`

## What it demonstrates

1. Knowledge Indexing API task for the `input/` directory.
2. Multi-file canonical ingestion (`.md/.txt/.json/.docx/.pdf/.xlsx/.pptx`) without manual dataset JSON assembly.
3. Generating the final report `output/release_readiness_report.md`.
4. Canonical document indexing smoke via Knowledge Factory MVP.
5. Write derived content blocks to `knowledge_blocks` read-model.
6. Retrieval over canonical `knowledge_blocks`.
7. Final markdown report with canonical quality summary and source mapping.
8. PDF table/form extraction path: `06_audit_summary.pdf` contains table-like and form-like layout (including multi-line form values ​​and rotated text line) to check `table_row` provenance.
9. PDF form-confidence policy gate: you can enable threshold and check `pdf_form_confidence_low` in `quality_summary`.

## Scripts

- Linux: `backend/scripts/demo_release_go_no_go_multifile_case.sh`
- Windows: `backend/scripts/demo_release_go_no_go_multifile_case.ps1`
- Canonical indexing smoke Linux: `backend/scripts/smoke_knowledge_indexing.sh`
- Canonical indexing smoke Windows: `backend/scripts/smoke_knowledge_indexing.ps1`
- Canonical indexing API task smoke Linux: `backend/scripts/smoke_knowledge_indexing_api.sh`
- Canonical indexing API task smoke Windows: `backend/scripts/smoke_knowledge_indexing_api.ps1`
- Canonical retrieval smoke Linux: `backend/scripts/smoke_canonical_retrieval.sh`
- Canonical retrieval smoke Windows: `backend/scripts/smoke_canonical_retrieval.ps1`
- Binary input generator Linux: `backend/scripts/build_binary_demo_documents.sh`
- Binary input generator Windows: `backend/scripts/build_binary_demo_documents.ps1`

To reassemble `.docx/.pdf/.xlsx/.pptx` inputs:

```bash
bash backend/scripts/build_binary_demo_documents.sh --overwrite
```

Smoke scripts also support the `--build-binary-demo-docs` flag to ensure that binary input files are present before execution.

The main demo script `demo_release_go_no_go_multifile_case.sh/.ps1` runs the canonical indexing API, then retrievals with `knowledge_source=canonical` and `canonical_doc_ids`, then updates `output/release_readiness_report.md`.

`smoke_knowledge_indexing.sh` and `smoke_knowledge_indexing_api.sh` now additionally print `pdf_demo_proof` for `06_audit_summary.pdf` to explicitly confirm table/form extraction on the actual PDF fixture.

Example of manual check of form-confidence threshold (warning mode):

```bash
APP_INDEXING_QUALITY_FORM_CONFIDENCE_MIN_SCORE=90 \
APP_INDEXING_QUALITY_FORM_CONFIDENCE_LOW_BLOCKING=false \
bash backend/scripts/smoke_knowledge_indexing_api.sh --build-binary-demo-docs
```

Example of manual OCR-confidence threshold (warning mode) check:

```bash
APP_INDEXING_QUALITY_OCR_CONFIDENCE_MIN_SCORE=70 \
APP_INDEXING_QUALITY_OCR_CONFIDENCE_LOW_BLOCKING=false \
bash backend/scripts/smoke_knowledge_indexing_api.sh --build-binary-demo-docs
```
