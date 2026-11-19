"""Research baselines, evidence checks, metrics, and experiment logging.

All deterministic semantic checks here are transparent heuristics. They are not
patent-law conclusions. The optional LLM judge is an experimental comparator.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .patent_eval import evaluate_case
except ImportError:  # direct module import from backend/
    from patent_eval import evaluate_case

EXPERIMENT_LOG = Path(os.getenv("PATENT_EXPERIMENT_LOG", "patent_experiments.jsonl"))


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def semantic_heuristic(case: dict[str, Any]) -> dict[str, Any]:
    """Low-cost lexical semantic proxy plus explicit contradiction/evidence checks."""
    source = case["source_claim"]
    candidate = case["candidate_output"]
    src, out = _tokens(source), _tokens(candidate)
    union = src | out
    similarity = len(src & out) / len(union) if union else 1.0
    negation = bool(re.search(r"\b(no|not|without|excluding)\b", source, re.I)) != bool(
        re.search(r"\b(no|not|without|excluding)\b", candidate, re.I)
    )
    evidence = case.get("evidence_quotes", [])
    evidence_missing = [quote for quote in evidence if quote.lower() not in candidate.lower()]
    findings = []
    if similarity < float(case.get("semantic_similarity_floor", 0.35)):
        findings.append({"code": "LOW_LEXICAL_OVERLAP", "message": f"Token overlap proxy is {similarity:.3f}; human review required."})
    if negation:
        findings.append({"code": "POSSIBLE_POLARITY_CHANGE", "message": "Negation markers differ between source and candidate; inspect manually."})
    if evidence_missing:
        findings.append({"code": "EVIDENCE_QUOTE_NOT_REPRODUCED", "message": "One or more configured evidence quotes are absent from the candidate."})
    return {"mode": "semantic_heuristic", "lexical_similarity": round(similarity, 4), "findings": findings,
            "evidence_quotes_missing": evidence_missing, "limitations": ["Lexical overlap is not semantic equivalence.", "No legal interpretation or external evidence retrieval is performed."]}


def llm_judge(case: dict[str, Any], model: str | None = None) -> dict[str, Any]:
    """Optional LLM comparator. Requires OPENAI_API_KEY; output is advisory and untrusted."""
    from openai import OpenAI
    client = OpenAI()
    selected_model = model or os.getenv("PATENT_JUDGE_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    prompt = {
        "source_claim": case["source_claim"],
        "candidate_output": case["candidate_output"],
        "evidence_ids": case.get("evidence_ids", []),
        "task": "Identify possible material omissions, unsupported additions, contradictions, and citation/evidence mismatches. Return JSON with risk_score 0-100, findings array of {code,severity,explanation}, and abstain boolean. Do not give legal advice."
    }
    start = time.perf_counter()
    response = client.responses.create(model=selected_model, instructions="You are an experimental patent-text QA evaluator. Be conservative. Distinguish observable text defects from legal conclusions. Output JSON only.", input=json.dumps(prompt))
    raw = response.output_text.strip()
    raw = re.sub(r"^\x60{3}(?:json)?|\x60{3}$", "", raw).strip()
    result = json.loads(raw)
    if not isinstance(result, dict) or not isinstance(result.get("findings", []), list):
        raise ValueError("LLM judge returned an invalid result schema")
    return {"mode": "llm_judge", "model": selected_model, "latency_ms": round((time.perf_counter()-start)*1000),
            "risk_score": max(0, min(100, int(result.get("risk_score", 0)))), "findings": result.get("findings", []),
            "abstain": bool(result.get("abstain", False)), "warning": "LLM output is non-deterministic and requires human review."}


def evaluate_hybrid(case: dict[str, Any], use_llm: bool = False) -> dict[str, Any]:
    rules = evaluate_case(case)
    semantic = semantic_heuristic(case)
    llm = None
    if use_llm:
        llm = llm_judge(case)
    # Hard deterministic failures remain visible; LLM output never suppresses a rule finding.
    return {"id": case["id"], "mode": "hybrid", "rule_result": rules, "semantic_result": semantic,
            "llm_result": llm, "combined_findings": rules["findings"] + semantic["findings"] +
            (llm["findings"] if llm else []), "human_review_required": bool(semantic["findings"] or llm)}


def classification_metrics(expected: list[set[str]], predicted: list[set[str]]) -> dict[str, float | int]:
    tp = sum(len(a & b) for a, b in zip(expected, predicted))
    fp = sum(len(b - a) for a, b in zip(expected, predicted))
    fn = sum(len(a - b) for a, b in zip(expected, predicted))
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"true_positives": tp, "false_positives": fp, "false_negatives": fn,
            "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
            "false_positive_rate_proxy": round(fp / (tp + fp) if tp + fp else 0.0, 4)}


def run_experiment(cases: list[dict[str, Any]], include_llm: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    expected = [set(c.get("expected_issue_codes", [])) for c in cases]
    rules = [evaluate_case(c) for c in cases]
    semantic = [semantic_heuristic(c) for c in cases]
    hybrid = [evaluate_hybrid(c, use_llm=include_llm) for c in cases]
    rule_pred = [set(r["detected_issue_codes"]) for r in rules]
    semantic_pred = [set(f["code"] for f in r["findings"]) for r in semantic]
    hybrid_pred = [set(r["rule_result"]["detected_issue_codes"]) | set(f["code"] for f in r["semantic_result"]["findings"]) for r in hybrid]
    report = {"experiment_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
              "created_at": datetime.now(timezone.utc).isoformat(), "dataset_size": len(cases),
              "llm_enabled": include_llm, "duration_ms": round((time.perf_counter()-started)*1000),
              "baselines": {"deterministic_rules": classification_metrics(expected, rule_pred),
                            "semantic_heuristic": classification_metrics(expected, semantic_pred),
                            "hybrid_rules_plus_heuristic": classification_metrics(expected, hybrid_pred)},
              "per_case": [{"id": c["id"], "rules": r, "semantic": s, "hybrid": h}
                           for c, r, s, h in zip(cases, rules, semantic, hybrid)],
              "caveat": "Synthetic fixture metrics only; issue-code coverage is not real-world patent QA accuracy."}
    EXPERIMENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with EXPERIMENT_LOG.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False) + "\n")
    return report
