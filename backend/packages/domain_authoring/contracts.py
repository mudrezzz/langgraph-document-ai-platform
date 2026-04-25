from __future__ import annotations

from domain_docs import InMemoryTemplateCatalog, TemplateCatalog, TemplateCompiler
from schemas.authoring.contracts import SectionContract
from schemas.documents.contracts import TemplateSpec
from schemas.rag.contracts import EvidencePack


class SectionContractBuilder:
    """Builds typed section contracts from evidence and review context."""

    def __init__(
        self,
        template_compiler: TemplateCompiler | None = None,
        template_catalog: TemplateCatalog | None = None,
    ) -> None:
        self._template_compiler = template_compiler or TemplateCompiler()
        self._template_catalog = template_catalog or InMemoryTemplateCatalog(compiler=self._template_compiler)

    def build_contracts_from_template(
        self,
        *,
        template_id: str,
        evidence_pack: EvidencePack,
        review_status: str,
        template_payload: dict | None = None,
        template_version: str | None = None,
    ) -> tuple[TemplateSpec, list[SectionContract]]:
        template_spec = self._resolve_template_spec(
            template_id=template_id,
            template_payload=template_payload,
            template_version=template_version,
        )
        return template_spec, self._contracts_from_spec(
            template_spec=template_spec,
            evidence_pack=evidence_pack,
            review_status=review_status,
        )

    def get_template_spec(
        self,
        *,
        template_id: str,
        template_payload: dict | None = None,
        template_version: str | None = None,
    ) -> TemplateSpec:
        return self._resolve_template_spec(
            template_id=template_id,
            template_payload=template_payload,
            template_version=template_version,
        )

    def build_release_readiness_contracts(
        self,
        *,
        evidence_pack: EvidencePack,
        review_status: str,
    ) -> list[SectionContract]:
        _, contracts = self.build_contracts_from_template(
            template_id="release_readiness",
            evidence_pack=evidence_pack,
            review_status=review_status,
        )
        return contracts

    def _contracts_from_spec(
        self,
        *,
        template_spec: TemplateSpec,
        evidence_pack: EvidencePack,
        review_status: str,
    ) -> list[SectionContract]:
        unique_sources = self._dedup_source_refs(evidence_pack)
        contracts: list[SectionContract] = []
        for section in template_spec.sections:
            section_id = str(section.get("section_id", "")).strip()
            title = str(section.get("title", section_id)).strip()
            objective = str(section.get("objective", f"Produce section {title}.")).strip()
            required_keywords = [str(item).strip() for item in section.get("required_keywords", []) if str(item).strip()]
            source_hints = tuple(
                str(item).strip() for item in (section.get("source_hints") or required_keywords) if str(item).strip()
            )
            preferred_source_refs = self._select_sources_by_keywords(
                evidence_pack=evidence_pack,
                keywords=source_hints,
                limit=3,
            )
            metadata = dict(section.get("metadata") or {})
            metadata["review_status"] = "informational" if metadata.get("informational") else review_status
            metadata["template_id"] = template_spec.template_id
            metadata["required"] = bool(section.get("required", True))
            metadata["include_if_has_evidence"] = bool(section.get("include_if_has_evidence", False))
            metadata["include_if_review_status"] = [
                str(item).strip().lower()
                for item in section.get("include_if_review_status", [])
                if str(item).strip()
            ]
            metadata["section_group"] = section.get("section_group")

            contracts.append(
                SectionContract(
                    section_id=section_id,
                    title=title,
                    objective=objective,
                    required_keywords=required_keywords,
                    preferred_source_refs=preferred_source_refs or unique_sources[:2],
                    metadata=metadata,
                )
            )
        return contracts

    def _resolve_template_spec(
        self,
        *,
        template_id: str,
        template_payload: dict | None = None,
        template_version: str | None = None,
    ) -> TemplateSpec:
        if template_payload is not None:
            return self._template_compiler.compile(
                template_id=template_id,
                template_payload=template_payload,
            )

        catalog_spec = self._template_catalog.get_template_spec(template_id, template_version)
        if catalog_spec is not None:
            return catalog_spec

        compiled = self._template_compiler.compile(template_id=template_id, template_payload=None)
        if template_version is not None:
            return compiled.model_copy(update={"version": str(template_version)})
        return compiled

    def _dedup_source_refs(self, evidence_pack: EvidencePack) -> list[dict[str, str]]:
        deduped: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for source in evidence_pack.selected_sources:
            key = (source.doc_id, source.version, source.block_id)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(
                {
                    "doc_id": source.doc_id,
                    "version": source.version,
                    "block_id": source.block_id,
                }
            )
        return deduped

    def _select_sources_by_keywords(
        self,
        *,
        evidence_pack: EvidencePack,
        keywords: tuple[str, ...],
        limit: int,
    ) -> list[dict[str, str]]:
        selected: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for block in evidence_pack.selected_blocks:
            lowered = block.text.lower()
            if not any(keyword in lowered for keyword in keywords):
                continue
            key = (block.source.doc_id, block.source.version, block.source.block_id)
            if key in seen:
                continue
            seen.add(key)
            selected.append(
                {
                    "doc_id": block.source.doc_id,
                    "version": block.source.version,
                    "block_id": block.source.block_id,
                }
            )
            if len(selected) >= limit:
                break
        return selected
