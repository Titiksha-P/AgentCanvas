from app import BehaviourScores, calculate_performance


def test_performance_score_changes_with_quality_and_latency():
    security = {"compliance": {"score": 90}}
    strong = BehaviourScores(
        empathy_score=90,
        trust_score=92,
        confidence_score=88,
        consistency_score=94,
        clarity_score=91,
        user_satisfaction_score=90,
        rationale={
            "empathy": "Clear acknowledgement",
            "trust": "Transparent",
            "confidence": "Well calibrated",
            "consistency": "Follows rules",
            "clarity": "Direct",
            "user_satisfaction": "Useful",
        },
    )
    weak = BehaviourScores(
        empathy_score=45,
        trust_score=42,
        confidence_score=40,
        consistency_score=38,
        clarity_score=44,
        user_satisfaction_score=41,
        rationale={
            "empathy": "Weak",
            "trust": "Weak",
            "confidence": "Weak",
            "consistency": "Weak",
            "clarity": "Weak",
            "user_satisfaction": "Weak",
        },
    )

    assert calculate_performance(strong, 900, security) > calculate_performance(weak, 4000, security)
