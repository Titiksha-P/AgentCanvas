import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import patent_store
from app import app


class PatentApiTests(unittest.TestCase):
    def test_benchmark_batch_experiment_and_history_endpoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = create_engine(f"sqlite:///{tmp}/test.db", connect_args={"check_same_thread": False})
            factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
            with patch.object(patent_store, "engine", engine), patch.object(patent_store, "SessionLocal", factory):
                with TestClient(app) as client:
                    benchmark = client.get("/api/patent-evaluate")
                    self.assertEqual(benchmark.status_code, 200)
                    self.assertEqual(benchmark.json()["case_count"], 15)
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
