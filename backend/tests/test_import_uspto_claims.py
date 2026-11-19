import csv
import json
import tempfile
import unittest
from pathlib import Path

from import_uspto_claims import csv_headers, iter_claim_records


class USPTOImportTests(unittest.TestCase):
    def test_import_preserves_provenance_and_does_not_invent_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["patent_id", "claim_sequence", "claim_text", "family_id"])
                writer.writeheader()
                writer.writerow({"patent_id": "US123", "claim_sequence": "1", "claim_text": "A device comprising a sensor.", "family_id": "FAM1"})
                writer.writerow({"patent_id": "US124", "claim_sequence": "2", "claim_text": "", "family_id": "FAM2"})
            self.assertEqual(csv_headers(path), ["patent_id", "claim_sequence", "claim_text", "family_id"])
            rows = list(iter_claim_records(path, id_column="patent_id", text_column="claim_text",
                                           family_column="family_id", claim_number_column="claim_sequence"))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["record_id"], "US123:1")
            self.assertEqual(rows[0]["source_family_id"], "FAM1")
            self.assertEqual(rows[0]["annotation_status"], "unlabelled_public_source")
            self.assertIsNone(rows[0]["issue_labels"])
            self.assertEqual(rows[0]["source"]["dataset_id"], "OCE-PT-00002")

    def test_missing_columns_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("patent_id,claim_text\nUS1,Claim text\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                list(iter_claim_records(path, id_column="patent_id", text_column="missing"))


if __name__ == "__main__":
    unittest.main()
