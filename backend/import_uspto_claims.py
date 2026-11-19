"""Stream-import USPTO public patent-claim CSV rows into provenance-preserving JSONL.

This utility does not invent candidate outputs or quality labels. Imported rows
remain unlabelled until a separate annotation workflow is completed.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterator


def csv_headers(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(next(csv.reader(stream), []))


def iter_claim_records(
    path: Path,
    *,
    id_column: str,
    text_column: str,
    family_column: str | None = None,
    claim_number_column: str | None = None,
    limit: int | None = None,
) -> Iterator[dict]:
    headers = set(csv_headers(path))
    required = {id_column, text_column}
    missing = required - headers
    if missing:
        raise ValueError(f"Missing required CSV columns: {', '.join(sorted(missing))}")
    for optional in (family_column, claim_number_column):
        if optional and optional not in headers:
            raise ValueError(f"Configured CSV column does not exist: {optional}")

    emitted = 0
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row_number, row in enumerate(csv.DictReader(stream), start=2):
            text = (row.get(text_column) or "").strip()
            if not text:
                continue
            document_id = (row.get(id_column) or "").strip()
            claim_number = (row.get(claim_number_column) or "").strip() if claim_number_column else ""
            family_id = (row.get(family_column) or "").strip() if family_column else ""
            record_id = f"{document_id}:{claim_number}" if claim_number else f"{document_id}:row-{row_number}"
            yield {
                "record_id": record_id,
                "source_document_id": document_id,
                "source_family_id": family_id or None,
                "claim_number": claim_number or None,
                "source_claim_text": text,
                "candidate_output_text": None,
                "issue_labels": None,
                "annotation_status": "unlabelled_public_source",
                "source": {
                    "dataset_id": "OCE-PT-00002",
                    "dataset_name": "USPTO Patent Claims Research Dataset",
                    "publisher": "United States Patent and Trademark Office, Office of the Chief Economist",
                    "license": "CC0 1.0 Public Domain Dedication",
                    "source_url": "https://data.uspto.gov/bulkdata/datasets/ptappclm",
                    "source_row_number": row_number,
                },
            }
            emitted += 1
            if limit is not None and emitted >= limit:
                break


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Downloaded USPTO CSV file")
    parser.add_argument("--output", type=Path, help="Output JSONL path (default: <input>.agentcanvas.jsonl)")
    parser.add_argument("--id-column", help="CSV column containing the patent/document identifier")
    parser.add_argument("--text-column", help="CSV column containing parsed claim text")
    parser.add_argument("--family-column", help="Optional family identifier column")
    parser.add_argument("--claim-number-column", help="Optional claim sequence/number column")
    parser.add_argument("--limit", type=int, help="Maximum non-empty claims to import")
    parser.add_argument("--show-header", action="store_true", help="Print CSV headers and exit")
    args = parser.parse_args()

    if args.show_header:
        print(json.dumps(csv_headers(args.input), indent=2))
        return
    if not args.id_column or not args.text_column:
        parser.error("--id-column and --text-column are required unless --show-header is used")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be a positive integer")

    output = args.output or args.input.with_suffix(".agentcanvas.jsonl")
    count = 0
    with output.open("w", encoding="utf-8") as stream:
        for record in iter_claim_records(
            args.input,
            id_column=args.id_column,
            text_column=args.text_column,
            family_column=args.family_column,
            claim_number_column=args.claim_number_column,
            limit=args.limit,
        ):
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    print(json.dumps({"output": str(output), "imported_claims": count, "labels_created": 0}, indent=2))


if __name__ == "__main__":
    main()
