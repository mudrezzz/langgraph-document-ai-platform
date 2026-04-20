#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from domain_rag.retrieval.release_packet_dataset import build_release_packet_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Преобразует release_packet.md в retrieval dataset JSON",
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="Путь до markdown release packet",
    )
    parser.add_argument(
        "--output-file",
        required=True,
        help="Путь до выходного dataset JSON",
    )
    parser.add_argument(
        "--dataset-id",
        default="release_go_no_go",
        help="Идентификатор датасета для retrieval workflow",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_file)
    output_path = Path(args.output_file)

    payload = build_release_packet_dataset(
        markdown_path=input_path,
        dataset_id=args.dataset_id,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"dataset_written: {output_path}")
    print(f"summary_blocks: {len(payload.get('summary_blocks', []))}")
    print(f"detail_blocks: {len(payload.get('detail_blocks', []))}")


if __name__ == "__main__":
    main()
