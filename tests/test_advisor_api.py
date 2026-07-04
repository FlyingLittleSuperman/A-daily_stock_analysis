# -*- coding: utf-8 -*-
"""Advisor copilot API regressions."""

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app import create_app
from src.services.advisor_copilot_service import AdvisorCopilotService


def test_advisor_status_and_run_api(tmp_path: Path) -> None:
    service = AdvisorCopilotService(storage_path=tmp_path / "advisor.json")

    with patch("api.middlewares.auth.is_auth_enabled", return_value=False):
        with patch("api.v1.endpoints.advisor.get_advisor_service", return_value=service):
            client = TestClient(create_app(static_dir=tmp_path / "static"))
            status_response = client.get("/api/v1/advisor/status")
            run_response = client.post(
                "/api/v1/advisor/run",
                json={"stage": "auction", "send_notification": False},
            )
            snapshots_response = client.get("/api/v1/advisor/snapshots")

    assert status_response.status_code == 200
    assert status_response.json()["stages"]
    assert run_response.status_code == 200
    assert run_response.json()["snapshot"]["stage"] == "auction"
    assert snapshots_response.status_code == 200
    assert snapshots_response.json()["items"][0]["stage"] == "auction"


def test_advisor_run_rejects_unknown_stage(tmp_path: Path) -> None:
    service = AdvisorCopilotService(storage_path=tmp_path / "advisor.json")

    with patch("api.middlewares.auth.is_auth_enabled", return_value=False):
        with patch("api.v1.endpoints.advisor.get_advisor_service", return_value=service):
            client = TestClient(create_app(static_dir=tmp_path / "static"))
            response = client.post(
                "/api/v1/advisor/run",
                json={"stage": "bad-stage", "send_notification": False},
            )

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
