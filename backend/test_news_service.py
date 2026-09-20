import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.services import news_service as news


class NewsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = patch.object(news, "DB_PATH", Path(self.temp.name) / "news.sqlite3")
        self.path.start()
        self.addCleanup(self.path.stop)
        app = FastAPI()
        app.include_router(news.router)
        self.client = TestClient(app)

    def test_reads_persist_without_search_or_expiration(self):
        self.assertEqual(self.client.get("/api/news?ticker=ENI.MI").json(), {"report": None})
        report = {"searched_at": "2020-01-01", "text": "saved"}
        news.save_report("ENI.MI", report)
        with patch("openai.OpenAI") as ai:
            self.assertEqual(self.client.get("/api/news?ticker=eni.mi").json()["report"], report)
            ai.assert_not_called()

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test"})
    def test_refresh_saves_and_failed_refresh_preserves(self):
        response = NS(status="completed", output_text="News fonte", output=[
            NS(type="web_search_call"), NS(type="message", content=[NS(type="output_text", text="News fonte",
                annotations=[NS(type="url_citation", start_index=5, end_index=10,
                                title="Fonte", url="https://example.com/news")])])])
        with patch("openai.OpenAI") as ai:
            api = MagicMock()
            ai.return_value.__enter__.return_value = api
            api.responses.create.return_value = response
            result = self.client.post("/api/news/research", json={"ticker": "ENI.MI"})
            self.assertEqual(result.status_code, 200)
            saved = result.json()["report"]
            self.assertIn("[Fonte](https://example.com/news)", saved["text"])
            call = api.responses.create.call_args.kwargs
            self.assertIn("latest close", call["input"])
            self.assertIn("Reuters MarketWatch London South East", call["input"])
            self.assertIn("Prezzo e movimento recente", call["instructions"])
            self.assertIn("Non mescolare mai azione ordinaria, ADR", call["instructions"])
            self.assertEqual(news.read_report("ENI.MI"), saved)
            api.responses.create.side_effect = RuntimeError("provider failure")
            self.assertEqual(self.client.post("/api/news/research", json={"ticker": "ENI.MI"}).status_code, 502)
            self.assertEqual(news.read_report("ENI.MI"), saved)

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test"})
    def test_concurrent_refresh_rejected(self):
        news._research_lock.acquire()
        try:
            self.assertEqual(self.client.post("/api/news/research", json={"ticker": "ENI.MI"}).status_code, 409)
        finally:
            news._research_lock.release()

    def test_london_listing_excludes_us_adr(self):
        brief = news.research_brief(news.ResearchRequest(ticker="VOD.L", name="Vodafone"), "2026-09-20")
        self.assertIn("London Stock Exchange", brief["listing_context"])
        self.assertIn("ADR", brief["listing_context"])
        self.assertIn("USD", brief["listing_context"])


if __name__ == "__main__":
    unittest.main()
