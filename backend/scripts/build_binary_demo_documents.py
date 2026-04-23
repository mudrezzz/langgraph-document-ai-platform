#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Генерирует DOCX/PDF входные документы для release go/no-go demo")
    parser.add_argument(
        "--output-dir",
        default="backend/examples/cases/release_go_no_go_multifile_case/input",
        help="Директория input demo-кейса",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Перезаписать существующие binary demo files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    written = build_binary_demo_documents(
        output_dir=Path(args.output_dir),
        overwrite=args.overwrite,
    )

    for path in written:
        print(f"written: {path}")
    if not written:
        print("binary_demo_documents: already_exist")


def build_binary_demo_documents(*, output_dir: Path, overwrite: bool = False) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)

    docx_path = output_dir / "05_release_notes.docx"
    pdf_path = output_dir / "06_audit_summary.pdf"

    written: list[str] = []
    if overwrite or not docx_path.exists():
        _write_docx(docx_path)
        written.append(str(docx_path))
    if overwrite or not pdf_path.exists():
        _write_pdf(pdf_path)
        written.append(str(pdf_path))
    return written


def _write_docx(path: Path) -> None:
    try:
        from docx import Document
    except Exception as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError("Для генерации DOCX demo требуется зависимость python-docx") from exc

    document = Document()
    document.add_heading("Release Notes: Payments v2", level=1)
    document.add_heading("Deployment Scope", level=2)
    document.add_paragraph("Payments v2 release includes API rollout, monitoring updates, and support handover.")
    document.add_paragraph("Feature flag rollout remains constrained until SRE approval is recorded.")
    document.add_heading("Known Limitations", level=2)
    document.add_paragraph("A rollback drill is documented, but the final go/no-go meeting must verify production readiness.")
    document.add_paragraph("Customer notification copy is ready and waiting for product owner sign-off.")
    document.save(path)


def _write_pdf(path: Path) -> None:
    try:
        import fitz
    except Exception as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError("Для генерации PDF demo требуется зависимость PyMuPDF") from exc

    doc = fitz.open()
    page = doc.new_page()
    text = (
        "Audit Summary: Payments v2\n\n"
        "Security audit status: conditional pass.\n"
        "Critical vulnerabilities: none open.\n"
        "Medium findings: two mitigated, one accepted with risk owner approval pending.\n\n"
        "Release control notes:\n"
        "- Evidence pack must include security sign-off.\n"
        "- Operations dashboard and rollback runbook must be attached before final approval.\n"
    )
    page.insert_text((72, 72), text, fontsize=11)
    doc.save(path)
    doc.close()


if __name__ == "__main__":
    main()
