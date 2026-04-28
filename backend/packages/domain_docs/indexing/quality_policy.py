from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from schemas.documents.contracts import CanonicalDocument

_DEFAULT_BLOCKING_FLAGS = frozenset(
    {
        "empty_document",
        "no_content_blocks",
        "pdf_no_extractable_text",
        "ocr_text_not_recovered",
    }
)


class IndexingDocumentQualityDecision(BaseModel):
    """Per-document indexing quality decision."""

    doc_id: str
    gate_status: Literal["passed", "warning", "failed"] = "passed"
    decision: Literal["accepted", "rejected"] = "accepted"
    accepted: bool = True
    quality_flags: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    warning_reasons: list[str] = Field(default_factory=list)


class IndexingQualityPolicyDecision(BaseModel):
    """Aggregated indexing quality policy decision."""

    policy_name: str
    gate_status: Literal["passed", "warning", "failed"] = "passed"
    documents_total: int = 0
    documents_with_flags: int = 0
    quality_flags_total: int = 0
    accepted_documents_total: int = 0
    rejected_documents_total: int = 0
    accepted_doc_ids: list[str] = Field(default_factory=list)
    rejected_doc_ids: list[str] = Field(default_factory=list)
    blocking_flags: list[str] = Field(default_factory=list)
    warning_flags: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    warning_reasons: list[str] = Field(default_factory=list)
    documents: dict[str, IndexingDocumentQualityDecision] = Field(default_factory=dict)


class KnowledgeIndexingQualityPolicy:
    """Configurable quality policy for canonical indexing decisions."""

    def __init__(
        self,
        *,
        policy_name: str = "default_indexing_quality_policy_v1",
        blocking_flags: set[str] | None = None,
        warning_only_flags: set[str] | None = None,
        allow_recovered_ocr: bool = True,
        ocr_recovery_blocking_flag: str = "pdf_no_extractable_text",
        ocr_recovery_success_flag: str = "ocr_applied",
    ) -> None:
        self.policy_name = policy_name
        self.blocking_flags = set(blocking_flags or _DEFAULT_BLOCKING_FLAGS)
        self.warning_only_flags = set(warning_only_flags or set())
        self.allow_recovered_ocr = allow_recovered_ocr
        self.ocr_recovery_blocking_flag = ocr_recovery_blocking_flag
        self.ocr_recovery_success_flag = ocr_recovery_success_flag

    def evaluate(
        self,
        *,
        documents: list[CanonicalDocument],
        quality_flags: list[str],
    ) -> IndexingQualityPolicyDecision:
        flags_by_doc = self._flags_by_doc(documents=documents, quality_flags=quality_flags)
        blocking_flags: list[str] = []
        warning_flags: list[str] = []
        seen_prefixed: set[str] = set()

        for flag in quality_flags:
            doc_id, flag_code = _split_quality_flag(flag)
            if doc_id is None:
                continue
            prefixed_flag = f"{doc_id}:{flag_code}"
            if prefixed_flag in seen_prefixed:
                continue
            seen_prefixed.add(prefixed_flag)
            target = blocking_flags if self._is_blocking(flag_code, set(flags_by_doc.get(doc_id, []))) else warning_flags
            target.append(prefixed_flag)

        for doc in documents:
            for flag_code in flags_by_doc.get(doc.doc_id, []):
                prefixed_flag = f"{doc.doc_id}:{flag_code}"
                if prefixed_flag in seen_prefixed:
                    continue
                seen_prefixed.add(prefixed_flag)
                target = (
                    blocking_flags
                    if self._is_blocking(flag_code, set(flags_by_doc.get(doc.doc_id, [])))
                    else warning_flags
                )
                target.append(prefixed_flag)

        document_decisions: dict[str, IndexingDocumentQualityDecision] = {}
        accepted_doc_ids: list[str] = []
        rejected_doc_ids: list[str] = []

        for doc in documents:
            doc_flags = flags_by_doc.get(doc.doc_id, [])
            doc_flag_set = set(doc_flags)
            doc_blocking = [f"{doc.doc_id}:{flag}" for flag in doc_flags if self._is_blocking(flag, doc_flag_set)]
            doc_warning = [f"{doc.doc_id}:{flag}" for flag in doc_flags if not self._is_blocking(flag, doc_flag_set)]
            accepted = not doc_blocking
            if accepted:
                accepted_doc_ids.append(doc.doc_id)
            else:
                rejected_doc_ids.append(doc.doc_id)

            document_decisions[doc.doc_id] = IndexingDocumentQualityDecision(
                doc_id=doc.doc_id,
                gate_status="failed" if doc_blocking else "warning" if doc_warning else "passed",
                decision="accepted" if accepted else "rejected",
                accepted=accepted,
                quality_flags=[f"{doc.doc_id}:{flag}" for flag in doc_flags],
                blocking_reasons=doc_blocking,
                warning_reasons=doc_warning,
            )

        gate_status: Literal["passed", "warning", "failed"]
        if rejected_doc_ids:
            gate_status = "failed"
        elif warning_flags:
            gate_status = "warning"
        else:
            gate_status = "passed"

        return IndexingQualityPolicyDecision(
            policy_name=self.policy_name,
            gate_status=gate_status,
            documents_total=len(documents),
            documents_with_flags=sum(1 for doc in documents if flags_by_doc.get(doc.doc_id)),
            quality_flags_total=len(quality_flags),
            accepted_documents_total=len(accepted_doc_ids),
            rejected_documents_total=len(rejected_doc_ids),
            accepted_doc_ids=accepted_doc_ids,
            rejected_doc_ids=rejected_doc_ids,
            blocking_flags=blocking_flags,
            warning_flags=warning_flags,
            blocking_reasons=list(blocking_flags),
            warning_reasons=list(warning_flags),
            documents=document_decisions,
        )

    def _flags_by_doc(
        self,
        *,
        documents: list[CanonicalDocument],
        quality_flags: list[str],
    ) -> dict[str, list[str]]:
        flags_by_doc: dict[str, list[str]] = {document.doc_id: [] for document in documents}

        for flag in quality_flags:
            doc_id, flag_code = _split_quality_flag(flag)
            if doc_id is None:
                continue
            flags_by_doc.setdefault(doc_id, [])
            if flag_code not in flags_by_doc[doc_id]:
                flags_by_doc[doc_id].append(flag_code)

        for document in documents:
            flags_by_doc.setdefault(document.doc_id, [])
            for flag_code in document.quality_flags:
                if flag_code not in flags_by_doc[document.doc_id]:
                    flags_by_doc[document.doc_id].append(flag_code)

        return flags_by_doc

    def _is_blocking(self, flag_code: str, doc_flags: set[str]) -> bool:
        if flag_code in self.warning_only_flags:
            return False
        if flag_code not in self.blocking_flags:
            return False
        if (
            self.allow_recovered_ocr
            and flag_code == self.ocr_recovery_blocking_flag
            and self.ocr_recovery_success_flag in doc_flags
        ):
            return False
        return True


def _split_quality_flag(flag: str) -> tuple[str | None, str]:
    if ":" not in flag:
        return None, flag
    doc_id, flag_code = flag.split(":", 1)
    return (doc_id or None), flag_code
