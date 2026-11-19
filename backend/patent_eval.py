"""Deterministic patent-output evaluation prototype.

The checks are research heuristics over synthetic fixtures, not legal advice,
claim construction, prior-art search, or a patentability opinion.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

try:
    from .cognisynth_adapter import CognisynthSafetyGate
except ImportError:  # direct module import from backend/
    from cognisynth_adapter import CognisynthSafetyGate

DATA_PATH = Path(__file__).with_name("patent_cases.json")


class PatentEvaluationCase(BaseModel):
    """Strict schema gate; unknown fixture fields are rejected."""
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    category: str = Field(min_length=1)
    source_claim: str = Field(min_length=1)
    candidate_output: str = Field(min_length=1)
    required_phrases: list[str] = Field(default_factory=list)
    unsupported_features: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_quotes: list[str] = Field(default_factory=list)
    invalid_dependency_references: list[int] = Field(default_factory=list)
    missing_antecedents: list[str] = Field(default_factory=list)
    expected_issue_codes: list[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    annotation_status: Literal["synthetic_test_oracle"] = "synthetic_test_oracle"
    annotation_rationale: str = ""
    evidence_spans: list[dict[str, str]] = Field(default_factory=list)
ISSUE_CODES = {"CLAIM_LIMITATION_OMITTED", "UNSUPPORTED_TECHNICAL_ASSERTION", "UNVERIFIED_PATENT_CITATION", "INVALID_CLAIM_DEPENDENCY", "ANTECEDENT_BASIS_MISSING", "EVIDENCE_QUOTE_NOT_REPRODUCED", "POSSIBLE_POLARITY_CHANGE"}

CITATION_RE = re.compile(r"\b(?:US|EP|WO)-?\d{4,}(?:-[A-Z]\d?)?\b", re.I)


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", _normalise(text)))


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    """Validate untrusted input, then run deterministic checks and return findings."""
    case = PatentEvaluationCase.model_validate(case).model_dump()
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

    for quote in case.get("evidence_quotes", []):
        if _normalise(quote) not in candidate:
            findings.append({"code": "EVIDENCE_QUOTE_NOT_REPRODUCED", "message": f"Configured evidence quote is absent from the candidate: {quote}"})

    source_negation = bool(re.search("(^|[^a-z])(no|not|without|excluding)([^a-z]|$)", source))
    candidate_negation = bool(re.search("(^|[^a-z])(no|not|without|excluding)([^a-z]|$)", candidate))
    if source_negation != candidate_negation:
        findings.append({"code": "POSSIBLE_POLARITY_CHANGE", "message": "Negation markers differ between source and candidate."})

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

    result = {
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
    return CognisynthSafetyGate().validate(result)


def run_benchmark(cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    if cases is None:
        cases = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    validated_cases = [PatentEvaluationCase.model_validate(case).model_dump() for case in cases]
    results = [evaluate_case(case) for case in validated_cases]
    expected_total = sum(len(item["expected_issue_codes"]) for item in results)
    tp = sum(item["true_positives"] for item in results)
    fp = sum(item["false_positives"] for item in results)
    fn = sum(item["false_negatives"] for item in results)
    precision = round(tp / (tp + fp), 4) if tp + fp else 1.0
    recall = round(tp / expected_total, 4) if expected_total else 1.0
    expected_sets = [set(item["expected_issue_codes"]) for item in results]
    detected_sets = [set(item["detected_issue_codes"]) for item in results]
    tn = sum(len(ISSUE_CODES - (a | b)) for a, b in zip(expected_sets, detected_sets))
    false_positive_rate = round(fp / (fp + tn), 4) if fp + tn else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0
    return {
        "benchmark_name": "AgentCanvas Patent Output Failure-Mode Benchmark",
        "benchmark_version": "0.2.0",
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
        "f1": f1,
        "true_negatives": tn,
        "false_positive_rate": false_positive_rate,
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "detection_rate_percent": round(recall * 100, 1),
        "results": results,
        "limitations": [
            "Fixtures and candidate outputs are synthetic and hand-authored.",
            "Checks use deterministic string and pattern heuristics, not a trained legal model.",
            "Citation membership does not establish that a cited document supports a proposition.",
            "This prototype does not assess novelty, inventive step, infringement, or legal sufficiency.",
        ],
    }
