from __future__ import annotations

from scripts.build_release_readiness_report import build_report_from_payloads


def test_release_readiness_report_includes_canonical_quality_and_source_mapping() -> None:
    report = build_report_from_payloads(
        task_id="retrieval-1",
        query="release readiness",
        status_payload={
            "status": "completed",
            "details": {
                "knowledge_source": "canonical",
                "retrieval_backend": "pgvector",
                "quality_gate_status": "warning",
                "confidence": 0.42,
            },
        },
        indexing_status_payload={
            "details": {
                "documents_total": 2,
                "file_types": ["docx", "pdf"],
                "embeddings_indexed": 3,
                "quality_gate_status": "warning",
                "quality_flags": ["PDF-1:low_text_density", "PDF-2:ocr_applied"],
                "quality_summary": {
                    "gate_status": "warning",
                    "quality_flags_total": 2,
                    "parser_families": ["docx", "pdf"],
                    "extraction_modes": ["page_text", "structured"],
                    "parser_issues_total": 3,
                    "documents_with_tables": 1,
                    "documents_needing_ocr": 1,
                },
                "parser_quality": {
                    "DOCX-1": {
                        "parser_family": "docx",
                        "blocks_total": 3,
                        "tables_total": 1,
                        "issues": [{"code": "table_extraction_not_implemented"}],
                    },
                    "PDF-1": {
                        "parser_family": "pdf",
                        "blocks_total": 1,
                        "tables_total": 0,
                        "issues": [{"code": "low_text_density"}],
                    },
                    "PDF-2": {
                        "parser_family": "pdf",
                        "blocks_total": 2,
                        "tables_total": 0,
                        "issues": [{"code": "ocr_applied"}],
                    },
                },
            },
        },
        evidence_payload={
            "evidence_pack": {
                "selected_sources": [
                    {"doc_id": "DOCX-1", "version": "1", "block_id": "B-1"},
                    {"doc_id": "PDF-1", "version": "1", "block_id": "B-1"},
                ],
                "unresolved_gaps": ["missing_required_document_types: methodology"],
                "confidence_notes": ["top_confidence=0.420"],
                "selected_blocks": [
                    {
                        "text": "Security approval PENDING",
                        "source": {"doc_id": "DOCX-1", "version": "1", "block_id": "B-1"},
                        "metadata": {
                            "file_type": "docx",
                            "source_path": "input/05_release_notes.docx",
                            "quality_flags": [],
                        },
                    },
                    {
                        "text": "Audit summary conditional pass",
                        "source": {"doc_id": "PDF-1", "version": "1", "block_id": "B-1"},
                        "metadata": {
                            "file_type": "pdf",
                            "source_path": "input/06_audit_summary.pdf",
                            "quality_flags": ["low_text_density"],
                        },
                    },
                ],
            }
        },
        events_summary_payload={
            "total_events": 2,
            "unique_tasks": 1,
            "transitions": [{"from_status": "running", "to_status": "completed", "total": 1}],
        },
    )

    assert "Knowledge source: `canonical`" in report
    assert "Retrieval backend: `pgvector`" in report
    assert "Retrieval quality gate: `warning`" in report
    assert "Confidence: `0.42`" in report
    assert "## Retrieval Quality" in report
    assert "`top_confidence=0.420`" in report
    assert "`missing_required_document_types: methodology`" in report
    assert "## Canonical Quality Summary" in report
    assert "quality_gate_status: `warning`" in report
    assert "`PDF-1:low_text_density`" in report
    assert "parser_families: `docx, pdf`" in report
    assert "documents_with_tables: `1`" in report
    assert "documents_needing_ocr: `1`" in report
    assert "### Parser Diagnostics" in report
    assert "doc_id=`DOCX-1`, parser_family=`docx`" in report
    assert "## Canonical Source Mapping" in report
    assert "source_path=`input/05_release_notes.docx`" in report
    assert "source_path=`input/06_audit_summary.pdf`" in report
