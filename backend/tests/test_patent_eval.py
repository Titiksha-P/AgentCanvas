import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patent_eval import run_benchmark


class PatentBenchmarkTests(unittest.TestCase):
    def test_all_five_synthetic_failures_are_detected(self):
        report = run_benchmark()
        self.assertEqual(report["case_count"], 5)
        self.assertEqual(report["cases_with_all_expected_failures_detected"], 5)
        self.assertEqual(report["false_negatives"], 0)
        self.assertEqual(report["false_positives"], 0)
        self.assertEqual(report["detection_rate_percent"], 100.0)

    def test_each_case_reports_findings_and_metrics(self):
        report = run_benchmark()
        for case in report["results"]:
            self.assertTrue(case["findings"])
            self.assertIn("precision", case)
            self.assertIn("recall", case)
            self.assertIn("score", case)


if __name__ == "__main__":
    unittest.main()
