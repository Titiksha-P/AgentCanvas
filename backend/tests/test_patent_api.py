import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import patent_store
import patent_api
from app import app


class PatentApiTests(unittest.TestCase):
    def test_production_write_endpoints_fail_closed_without_token(self):
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=False):
            os.environ.pop("AGENTCANVAS_API_TOKEN", None)
            with TestClient(app) as client:
                response = client.post("/api/patent-evaluate")
                self.assertEqual(response.status_code, 503)

    def test_production_write_endpoints_require_bearer_token(self):
        with patch.dict(os.environ, {"APP_ENV": "production", "AGENTCANVAS_API_TOKEN": "test-secret"}, clear=False):
            with TestClient(app) as client:
                denied = client.post("/api/patent-evaluate")
                self.assertEqual(denied.status_code, 401)
                with patch.object(patent_api, "run_benchmark", return_value={
                    "case_count": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "results": []
                }), patch.object(patent_api, "save_evaluation", return_value=123):
                    allowed = client.post("/api/patent-evaluate", headers={"Authorization": "Bearer test-secret"})
                self.assertEqual(allowed.status_code, 200)
                self.assertEqual(allowed.json()["history_id"], 123)

    def test_database_health_checks_live_schema_without_returning_secrets(self):
        connection = MagicMock()
        table_result = MagicMock()
        table_result.scalar.return_value = "public.patent_evaluations"
        connection.execute.side_effect = [None, table_result]
        fake_engine = MagicMock()
        fake_engine.connect.return_value.__enter__.return_value = connection
        with patch.dict(os.environ, {"APP_ENV": "production", "DATABASE_URL": "postgresql://redacted"}):
            with patch.object(patent_api, "engine", fake_engine):
                with TestClient(app) as client:
                    response = client.get("/api/patent-db-health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertNotIn("redacted", response.text)

    def test_benchmark_batch_experiment_and_history_endpoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = create_engine(f"sqlite:///{tmp}/test.db", connect_args={"check_same_thread": False})
            factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
            with patch.object(patent_store, "engine", engine), patch.object(patent_store, "SessionLocal", factory):
                with TestClient(app) as client:
                    preview = client.get("/api/patent-evaluate")
                    self.assertEqual(preview.status_code, 200)
                    benchmark = client.post("/api/patent-evaluate")
                    self.assertEqual(benchmark.status_code, 200)
                    self.assertEqual(benchmark.json()["case_count"], 20)
                    self.assertTrue(benchmark.json()["results"][0]["safety_gate"]["accepted"])

                    cases = json.loads((BACKEND / "patent_cases.json").read_text(encoding="utf-8"))
                    batch = client.post("/api/patent-evaluate/batch", json={"cases": cases[:2]})
                    self.assertEqual(batch.status_code, 200)
                    self.assertEqual(batch.json()["case_count"], 2)
                    self.assertIn("findings", batch.json()["results"][0])

                    experiment = client.post("/api/patent-experiments", json={"include_llm": False})
                    self.assertEqual(experiment.status_code, 200)
                    self.assertFalse(experiment.json()["llm_enabled"])
                    self.assertIn("llm_judge", experiment.json()["baselines"])

                    history = client.get("/api/patent-history?limit=10")
                    self.assertEqual(history.status_code, 200)
                    self.assertEqual(len(history.json()["items"]), 3)


if __name__ == "__main__":
    unittest.main()
