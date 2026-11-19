"""Patent benchmark, batch, experiment and history API routes."""
from __future__ import annotations
import json
import os
import os
import hmac
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

try:
    from .patent_eval import run_benchmark, evaluate_case, PatentEvaluationCase
    from .patent_research import run_experiment, evaluate_hybrid
    from .patent_store import DATABASE_URL, engine, save_evaluation, list_evaluations
except ImportError:  # uvicorn app:app when launched inside backend/
    from patent_eval import run_benchmark, evaluate_case, PatentEvaluationCase
    from patent_research import run_experiment, evaluate_hybrid
    from patent_store import DATABASE_URL, engine, save_evaluation, list_evaluations

router = APIRouter()

def require_write_access(authorization: str | None = Header(default=None)) -> None:
    """Require a server-side bearer token for mutating endpoints in production."""
    token = os.getenv("AGENTCANVAS_API_TOKEN")
    production = os.getenv("APP_ENV", "").lower() == "production"
    if production and not token:
        raise HTTPException(status_code=503, detail="Write endpoints are disabled until AGENTCANVAS_API_TOKEN is configured.")
    if token and not hmac.compare_digest(authorization or "", f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="A valid bearer token is required.")

CASES_PATH = Path(__file__).with_name("patent_cases.json")

class BatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cases: list[PatentEvaluationCase] = Field(min_length=1, max_length=100)
    include_llm: bool = False

class ExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    include_llm: bool = False


@router.get("/api/patent-db-health")
def patent_db_health() -> dict[str, Any]:
    """Non-sensitive readiness check for the configured production database."""
    if not os.getenv("DATABASE_URL"):
        return {"status": "not_configured", "message": "Set DATABASE_URL in the backend deployment environment."}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            table_exists = connection.execute(
                text("SELECT to_regclass('public.patent_evaluations')")
            ).scalar() is not None
        if not table_exists:
            return {"status": "schema_missing", "message": "Apply the patent_evaluations migration."}
        return {"status": "ok", "table": "public.patent_evaluations"}
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Check DATABASE_URL, password, SSL, and pooler settings.",
        )

@router.get("/api/patent-evaluate")
def patent_evaluate() -> dict[str, Any]:
    """Read-only benchmark preview; does not write evaluation history."""
    try:
        return run_benchmark()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Patent benchmark failed closed: {exc}") from exc


@router.post("/api/patent-evaluate", dependencies=[Depends(require_write_access)])
def save_patent_evaluation() -> dict[str, Any]:
    """Execute and persist a benchmark run."""
    try:
        result = run_benchmark()
        record_id = save_evaluation("rules", {"case_count": result["case_count"], "precision": result["precision"],
            "recall": result["recall"], "f1": result.get("f1")}, result)
        result["history_id"] = record_id
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Patent benchmark failed closed: {exc}") from exc


@router.post("/api/patent-evaluate/batch", dependencies=[Depends(require_write_access)])
def patent_evaluate_batch(request: BatchRequest) -> dict[str, Any]:
    try:
        cases = [item.model_dump() for item in request.cases]
        # Bounded in-process concurrency; requests are capped at 100 cases.
        with ThreadPoolExecutor(max_workers=min(8, len(cases))) as pool:
            results = list(pool.map(lambda case: evaluate_hybrid(case, use_llm=request.include_llm), cases))
        for source, result in zip(cases, results):
            result.update({"title": source["title"], "category": source["category"],
                           "source_claim": source["source_claim"], "candidate_output": source["candidate_output"],
                           "findings": result["combined_findings"]})
        summary = {"case_count": len(results), "llm_enabled": request.include_llm,
                   "finding_count": sum(len(item["combined_findings"]) for item in results)}
        record_id = save_evaluation("batch_hybrid", summary, {"results": results})
        return {"history_id": record_id, **summary, "results": results}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Batch evaluation failed: {exc}") from exc

@router.post("/api/patent-experiments", dependencies=[Depends(require_write_access)])
def patent_experiments(request: ExperimentRequest) -> dict[str, Any]:
    try:
        cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
        report = run_experiment(cases, include_llm=request.include_llm)
        record_id = save_evaluation("experiment", report["baselines"], report)
        report["history_id"] = record_id
        return report
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Experiment failed: {exc}") from exc

@router.get("/api/patent-history", dependencies=[Depends(require_write_access)])
def patent_history(limit: int = 25) -> dict[str, Any]:
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    try:
        return {"items": list_evaluations(limit)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Evaluation history unavailable: {exc}") from exc
