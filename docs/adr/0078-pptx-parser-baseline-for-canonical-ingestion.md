# ADR-0078: PPTX parser baseline for canonical ingestion

- Status: Accepted
- Date: 2026-04-28

## Context

After slices with DOCX/XLSX/PDF/OCR in Increment 31, the last format from the target baseline of the first production circuit remained in canonical ingestion - `.pptx`.

Without PPTX parser, presentation artifacts (release briefings, steering decks, risk reviews) fell out of the single Knowledge Factory path and required manual duplication of content in `.md/.docx`.

## Solution

1. Add `.pptx` to `CanonicalDocumentParser.supported_extensions()`.
2. Implement parser path via `python-pptx`:
- slides become structural sections;
- title/body content is saved in canonical blocks (`slide_title`, `paragraph`, `bullet`);
- speaker notes are saved as canonical `note` blocks.
3. Expand parser diagnostics flags:
   - `pptx_slides_detected`;
   - `pptx_notes_detected`.
4. Expand the binary demo input with a new fixture `09_release_briefing.pptx` via the existing generator `build_binary_demo_documents.py`.
5. Do not introduce a separate presentation-specific retrieval/indexing stack - PPTX reuse the current canonical/indexing/vector path.

## Consequences

Pros:

- canonical ingestion covers another production-relevant enterprise format;
- multi-file demo actually checks presentation ingestion in manual smoke path;
- `.pptx` content immediately goes into the retrieval corpus and traceability path.

Cons:

- baseline parser does not yet extract images/diagrams/rich layout geometry;
- table-aware extraction for PPTX remains the future enrichment slice;
- notes extraction depends on how full speaker notes are in the original presentation.
