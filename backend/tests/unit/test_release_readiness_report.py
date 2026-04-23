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
            },
        },
        indexing_status_payload={
            "details": {
                "documents_total": 2,
                "file_types": ["docx", "pdf"],
                "embeddings_indexed": 3,
                "quality_gate_status": "warning",
                "quality_flags": ["PDF-1:low_text_density"],
                "quality_summary": {
                    "gate_status": "warning",
                    "quality_flags_total": 1,
                },
            },
        },
        evidence_payload={
            "evidence_pack": {
                "selected_sources": [
                    {"doc_id": "DOCX-1", "version": "1", "block_id": "B-1"},
                    {"doc_id": "PDF-1", "version": "1", "block_id": "B-1"},
                ],
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
    assert "## Canonical Quality Summary" in report
    assert "quality_gate_status: `warning`" in report
    assert "`PDF-1:low_text_density`" in report
    assert "## Canonical Source Mapping" in report
    assert "source_path=`input/05_release_notes.docx`" in report
    assert "source_path=`input/06_audit_summary.pdf`" in report
