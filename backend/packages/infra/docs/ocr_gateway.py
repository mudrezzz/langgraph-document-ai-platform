from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from domain_docs.parsing.ocr import PdfOcrGateway, PdfOcrResult


class SidecarPdfOcrGateway(PdfOcrGateway):
    """Deterministic OCR fallback that reads text from a sidecar `.ocr.txt` file."""

    def extract_pdf_text(self, pdf_path: str | Path) -> PdfOcrResult | None:
        path = Path(pdf_path)
        candidates = [path.with_suffix(path.suffix + ".ocr.txt"), path.with_suffix(".ocr.txt")]
        for candidate in candidates:
            if candidate.exists():
                raw = candidate.read_text(encoding="utf-8")
                page_texts = [chunk.strip() for chunk in raw.split("\f") if chunk.strip()]
                if not page_texts and raw.strip():
                    page_texts = [raw.strip()]
                if not page_texts:
                    return None
                return PdfOcrResult(page_texts=page_texts, provider="sidecar")
        return None


class OcrmypdfGateway(PdfOcrGateway):
    """Optional real OCR adapter backed by the `ocrmypdf` CLI."""

    def __init__(self, *, sidecar_gateway: PdfOcrGateway | None = None) -> None:
        self._sidecar_gateway = sidecar_gateway or SidecarPdfOcrGateway()

    def extract_pdf_text(self, pdf_path: str | Path) -> PdfOcrResult | None:
        input_path = Path(pdf_path)
        output_dir = Path(tempfile.mkdtemp(prefix="ocrmypdf-"))
        output_pdf = output_dir / input_path.name
        language = os.getenv("APP_OCR_LANGUAGE", "eng")
        timeout_sec = int(os.getenv("APP_OCR_TIMEOUT_SEC", "120"))
        command = [
            "ocrmypdf",
            "--force-ocr",
            "--sidecar",
            str(output_dir / "sidecar.txt"),
            "-l",
            language,
            str(input_path),
            str(output_pdf),
        ]

        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_sec, check=False)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return self._sidecar_gateway.extract_pdf_text(input_path)

        sidecar_path = output_dir / "sidecar.txt"
        warnings: list[str] = []
        if completed.returncode != 0:
            warnings.append("ocr_cli_failed")
        if completed.stderr.strip():
            warnings.append("ocr_cli_stderr")
        if not sidecar_path.exists():
            fallback = self._sidecar_gateway.extract_pdf_text(input_path)
            if fallback is None:
                return None
            fallback.warnings.extend(warnings)
            fallback.warnings.append("ocr_sidecar_fallback")
            return fallback

        raw = sidecar_path.read_text(encoding="utf-8", errors="ignore")
        page_texts = [chunk.strip() for chunk in raw.split("\f") if chunk.strip()]
        if not page_texts and raw.strip():
            page_texts = [raw.strip()]
        if not page_texts:
            return None
        return PdfOcrResult(page_texts=page_texts, provider="ocrmypdf", warnings=warnings)

