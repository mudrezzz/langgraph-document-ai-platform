from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field


class PdfOcrResult(BaseModel):
    """Normalized OCR output for one PDF document."""

    page_texts: list[str] = Field(default_factory=list)
    provider: str = "sidecar"
    warnings: list[str] = Field(default_factory=list)


class PdfOcrGateway(Protocol):
    """Boundary for OCR extraction from scanned PDF files."""

    def extract_pdf_text(self, pdf_path: str | Path) -> PdfOcrResult | None:
        """Return OCR text grouped by pages, or None when OCR did not recover text."""

