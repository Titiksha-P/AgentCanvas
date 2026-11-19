"""Cognisynth-inspired fail-closed invariant adapter for patent evaluations.

This module adapts the safety-gate pattern to the patent domain. It deliberately
does not import Cognisynth's UI blueprint validator: UI reachability and frame
budget rules are not patent-claim rules.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, ValidationError

class GateFinding(BaseModel):
    model_config = ConfigDict(extra="allow")
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)

class GateResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(min_length=1)
    findings: list[GateFinding]
    detected_issue_codes: list[str]
    true_positives: int = Field(ge=0)
    false_positives: int = Field(ge=0)
    false_negatives: int = Field(ge=0)
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    score: int = Field(ge=0, le=100)
    matched_expected_failures: bool

class CognisynthSafetyGate:
    """Validate evaluator output as untrusted data before it reaches API/UI layers."""
    def validate(self, result: dict[str, Any]) -> dict[str, Any]:
        try:
            checked = GateResult.model_validate(result)
        except ValidationError as exc:
            raise ValueError("Cognisynth safety gate rejected malformed evaluator output") from exc
        codes = [finding.code for finding in checked.findings]
        if set(codes) != set(checked.detected_issue_codes):
            raise ValueError("Cognisynth safety gate rejected inconsistent finding codes")
        if checked.matched_expected_failures and checked.false_negatives:
            raise ValueError("Cognisynth safety gate rejected inconsistent success state")
        return {**checked.model_dump(), "safety_gate": {"accepted": checked.false_negatives == 0 and checked.false_positives == 0,
            "gate": "cognisynth_invariant_adapter", "fail_closed": True}}

