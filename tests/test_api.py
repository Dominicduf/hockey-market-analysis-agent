import asyncio
from unittest.mock import AsyncMock, patch

import httpx
from langchain_core.messages import AIMessage
from openai import RateLimitError
from starlette.testclient import TestClient

from app.agent import agent
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_success_returns_response():
    mock_result = {"messages": [AIMessage(content="Report at GET /reports/report.pdf")]}
    with patch.object(agent, "ainvoke", new_callable=AsyncMock, return_value=mock_result):
        response = client.post("/analyze", json={"query": "Analyze hockey sticks"})

    assert response.status_code == 200
    assert response.json()["response"] == "Report at GET /reports/report.pdf"


def test_analyze_timeout_returns_504():
    with patch.object(agent, "ainvoke", new_callable=AsyncMock, side_effect=asyncio.TimeoutError()):
        response = client.post("/analyze", json={"query": "Analyze hockey sticks"})

    assert response.status_code == 504


def test_analyze_rate_limit_returns_429():
    mock_request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    mock_response = httpx.Response(429, request=mock_request)
    error = RateLimitError("rate limit exceeded", response=mock_response, body=None)

    with patch.object(agent, "ainvoke", new_callable=AsyncMock, side_effect=error):
        response = client.post("/analyze", json={"query": "Analyze hockey sticks"})

    assert response.status_code == 429


def test_download_existing_report_returns_pdf(tmp_path):
    fake_pdf = tmp_path / "report_test.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake content")

    with patch("app.main.REPORTS_DIR", tmp_path):
        response = client.get("/reports/report_test.pdf")

    assert response.status_code == 200
    assert "pdf" in response.headers["content-type"]


def test_download_missing_report_returns_404():
    response = client.get("/reports/does_not_exist.pdf")
    assert response.status_code == 404
