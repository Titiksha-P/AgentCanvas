import json
import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from patent_eval import PatentEvaluationCase, evaluate_case, run_benchmark
from patent_research import classification_metrics, semantic_heuristic, run_experiment


class PatentBenchmarkTests(unittest.TestCase):
    def test_all_twenty_synthetic_cases_are_evaluated(self):
        report = run_benchmark()
        self.assertEqual(report["case_count"], 20)
        self.assertEqual(report["cases_with_all_expected_failures_detected"], 20)
        self.assertGreater(report["true_negatives"], 0)
        self.assertEqual(report["false_positive_rate"], 0.0)
        self.assertEqual(report["false_negatives"], 0)
        self.assertEqual(report["false_positives"], 0)
        self.assertEqual(report["detection_rate_percent"], 100.0)

    def test_each_case_reports_findings_and_metrics(self):
        report = run_benchmark()
        for case in report["results"]:
            if case["expected_issue_codes"]:
                self.assertTrue(case["findings"])
            else:
                self.assertEqual(case["findings"], [])
            self.assertIn("precision", case)
            self.assertIn("recall", case)
            self.assertIn("score", case)

    def test_strict_schema_rejects_unknown_fields(self):
        with self.assertRaises(ValueError):
            PatentEvaluationCase.model_validate({"id": "x", "title": "x", "category": "x",
                "source_claim": "x", "candidate_output": "x", "unexpected": True})

    def test_metrics_are_computed_correctly(self):
        result = classification_metrics([{"A", "B"}], [{"A", "C"}])
        self.assertEqual(result["true_positives"], 1)
        self.assertEqual(result["false_positives"], 1)
        self.assertEqual(result["false_negatives"], 1)
        self.assertEqual(result["f1"], 0.5)

    def test_semantic_heuristic_returns_explicit_mode_and_findings(self):
        result = semantic_heuristic({"source_claim": "A device without a battery.",
            "candidate_output": "A device with a battery.", "evidence_quotes": ["exact support"]})
        self.assertEqual(result["mode"], "semantic_heuristic")
        self.assertTrue(result["findings"])

    def test_cognisynth_gate_marks_clean_fixture_as_accepted(self):
        case = json.loads((BACKEND / "patent_cases.json").read_text(encoding="utf-8"))[0]
        result = evaluate_case(case)
        self.assertTrue(result["safety_gate"]["accepted"])
        self.assertEqual(result["safety_gate"]["gate"], "cognisynth_invariant_adapter")

    def test_experiment_report_contains_comparable_baselines(self):
        cases = json.loads((BACKEND / "patent_cases.json").read_text(encoding="utf-8"))
        report = run_experiment(cases[:3], include_llm=False)
        self.assertEqual(report["dataset_size"], 3)
        self.assertIn("deterministic_rules", report["baselines"])
        self.assertIn("semantic_heuristic", report["baselines"])
        self.assertIn("hybrid_rules_semantic_llm", report["baselines"])


if __name__ == "__main__":
    unittest.main()
