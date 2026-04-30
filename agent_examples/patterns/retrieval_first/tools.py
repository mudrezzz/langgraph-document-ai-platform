from __future__ import annotations

from schemas.rag.contracts import RetrievalFilter


DEFAULT_PROJECT_ID = "p1"
DEFAULT_DOCUMENT_TYPES = ["requirements", "methodology", "security", "operations", "governance"]


def build_default_filters() -> RetrievalFilter:
    """Return baseline retrieval filters used by the demo agent.

    The function is intentionally small and explicit so developers can copy this
    file and customize filters for their own corpus quickly.
    """

    return RetrievalFilter(project_id=DEFAULT_PROJECT_ID, document_types=list(DEFAULT_DOCUMENT_TYPES))
