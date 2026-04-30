from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEVELOPER_GUIDE_ROOT = REPO_ROOT / "docs" / "developer_guide"


def test_developer_guide_index_links_expected_pages() -> None:
    index = (DEVELOPER_GUIDE_ROOT / "README.md").read_text(encoding="utf-8")

    required_pages = [
        "docs/developer_guide/quickstart.md",
        "docs/developer_guide/manual_demo_checks.md",
        "docs/developer_guide/extension_recipes.md",
        "docs/developer_guide/operations_and_release.md",
    ]

    for page in required_pages:
        assert page in index
        assert (REPO_ROOT / page).exists(), page


def test_operations_and_release_documents_mandatory_full_gate_command() -> None:
    operations = (DEVELOPER_GUIDE_ROOT / "operations_and_release.md").read_text(encoding="utf-8")

    for required_fragment in [
        "RUN_DOCKER_ASYNC_E2E=1",
        "RUN_EXTERNAL_LLM_TESTS=1",
        ".venv/bin/pytest backend/tests -rs",
        "awk -F= '/^OPENROUTER_API_KEY=/",
        "awk -F= '/^OPENROUTER_MODEL=/",
        "awk -F= '/^OPENROUTER_BASE_URL=/",
    ]:
        assert required_fragment in operations

    assert "set -a && source backend/.env && set +a" not in operations


def test_manual_demo_checks_cover_pdf_and_pptx_proof() -> None:
    manual = (DEVELOPER_GUIDE_ROOT / "manual_demo_checks.md").read_text(encoding="utf-8")

    for required_fragment in [
        "smoke_knowledge_indexing_api.sh",
        "--build-binary-demo-docs",
        "parser_family==\"pptx\"",
        "pdf_demo_proof",
        "demo_release_go_no_go_multifile_case.sh",
        "release_readiness_report.md",
    ]:
        assert required_fragment in manual
