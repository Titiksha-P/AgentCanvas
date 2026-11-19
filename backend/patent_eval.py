"""Deterministic patent-output evaluation prototype.

The checks are research heuristics over synthetic fixtures, not legal advice,
claim construction, prior-art search, or a patentability opinion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).with_name("patent_cases.json")
CITATION_RE = re.compile(r"\b(?:US|EP|WO)-?\d{4,}(?:-[A-Z]\d?)?\b", re.I)


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", _normalise(text)))


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run deterministic checks and return explicit, inspectable findings."""
    source = _normalise(case["source_claim"])
    candidate = _normalise(case["candidate_output"])
    evidence_ids = {str(item).upper() for item in case.get("evidence_ids", [])}
    findings: list[dict[str, str]] = []

    required_phrases = case.get("required_phrases", [])
    for phrase in required_phrases:
        if _normalise(phrase) not in candidate:
            findings.append({
                "code": "CLAIM_LIMITATION_OMITTED",
                "message": f"Required source limitation is absent: {phrase}",
            })

    for feature in case.get("unsupported_features", []):
        if _normalise(feature) in candidate and _normalise(feature) not in source:
            findings.append({
                "code": "UNSUPPORTED_TECHNICAL_ASSERTION",
                "message": f"Candidate introduces a feature not present in the source: {feature}",
            })

    for citation in CITATION_RE.findall(case["candidate_output"]):
        if citation.upper() not in evidence_ids:
            findings.append({
                "code": "UNVERIFIED_PATENT_CITATION",
                "message": f"Citation {citation} is not present in the supplied evidence set.",
            })

    for reference in case.get("invalid_dependency_references", []):
        if re.search(rf"\bclaim\s+{int(reference)}\b", candidate, re.I):
            findings.append({
                "code": "INVALID_CLAIM_DEPENDENCY",
                "message": f"Dependency points to unavailable or later claim {reference}.",
            })

    for term in case.get("missing_antecedents", []):
        # A use of "the X" without an earlier "a/an X" is a drafting signal.
        if re.search(rf"\bthe\s+{re.escape(term)}\b", candidate, re.I) and not re.search(
            rf"\b(?:a|an)\s+{re.escape(term)}\b", candidate, re.I
        ):
            findings.append({
                "code": "ANTECEDENT_BASIS_MISSING",
                "message": f"'{term}' is used as a definite element without an earlier introduction.",
            })

    expected = set(case.get("expected_issue_codes", []))
    detected = {item["code"] for item in findings}
    true_positive = len(expected & detected)
    false_negative = len(expected - detected)
    false_positive = len(detected - expected)
    denominator = true_positive + false_negative
    recall = round(true_positive / denominator, 4) if denominator else 1.0
    precision_denominator = true_positive + false_positive
    precision = round(true_positive / precision_denominator, 4) if precision_denominator else 1.0

    return {
        "id": case["id"],
        "title": case["title"],
        "category": case["category"],
        "source_claim": case["source_claim"],
        "candidate_output": case["candidate_output"],
        "expected_issue_codes": sorted(expected),
        "findings": findings,
        "detected_issue_codes": sorted(detected),
        "true_positives": true_positive,
        "false_positives": false_positive,
        "false_negatives": false_negative,
        "precision": precision,
        "recall": recall,
        "score": round(100 * recall),
        "matched_expected_failures": expected <= detected,
    }


def run_benchmark(cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if cases is None:
        cases = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    results = [evaluate_case(case) for case in cases]
    expected_total = sum(len(item["expected_issue_codes"]) for item in results)
    tp = sum(item["true_positives"] for item in results)
    fp = sum(item["false_positives"] for item in results)
    fn = sum(item["false_negatives"] for item in results)
    precision = round(tp / (tp + fp), 4) if tp + fp else 1.0
    recall = round(tp / expected_total, 4) if expected_total else 1.0
    return {
        "benchmark_name": "AgentCanvas Patent Output Failure-Mode Benchmark",
        "benchmark_version": "0.1.0",
        "evaluation_mode": "deterministic_rules_over_synthetic_fixtures",
        "case_count": len(results),
        "cases_with_all_expected_failures_detected": sum(
            1 for item in results if item["matched_expected_failures"]
        ),
        "expected_issue_count": expected_total,
        "detected_expected_issues": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": precision,
        "recall": recall,
        "detection_rate_percent": round(recall * 100, 1),
        "results": results,
        "limitations": [
            "Fixtures and candidate outputs are synthetic and hand-authored.",
            "Checks use deterministic string and pattern heuristics, not a trained legal model.",
            "Citation membership does not establish that a cited document supports a proposition.",
            "This prototype does not assess novelty, inventive step, infringement, or legal sufficiency.",
        ],
    }
