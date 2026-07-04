# -*- coding: utf-8 -*-
"""Advisor copilot service regressions."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.notification import ChannelAttemptResult, NotificationChannel, NotificationDispatchResult
from src.services.advisor_copilot_service import AdvisorCopilotService


def test_run_stage_persists_structured_snapshot(tmp_path: Path) -> None:
    service = AdvisorCopilotService(storage_path=tmp_path / "advisor.json")

    result = service.run_stage("open_confirm")

    snapshot = result["snapshot"]
    assert snapshot["stage"] == "open_confirm"
    assert snapshot["stage_name"] == "开盘主线确认"
    assert snapshot["action_level"] == "条件参与"
    assert snapshot["candidates"]
    assert "免责声明" in snapshot["markdown"]
    assert service.list_snapshots()[0]["id"] == snapshot["id"]


def test_status_reports_configured_notification_channels(tmp_path: Path) -> None:
    service = AdvisorCopilotService(storage_path=tmp_path / "advisor.json")

    with patch(
        "src.services.advisor_copilot_service.NotificationService.detect_configured_channels",
        return_value=[NotificationChannel.FEISHU, NotificationChannel.WECHAT],
    ):
        status = service.get_status()

    assert status["enabled"] is True
    assert status["notification_ready"] is True
    assert status["notification_channels"] == ["feishu", "wechat"]
    assert status["next_stage"]["id"]


def test_send_notification_records_channel_result(tmp_path: Path) -> None:
    service = AdvisorCopilotService(storage_path=tmp_path / "advisor.json")
    notification_service = MagicMock()
    notification_service.send_with_results.return_value = NotificationDispatchResult(
        dispatched=True,
        success=True,
        status="sent",
        channel_results=[ChannelAttemptResult(channel="feishu", success=True, latency_ms=12)],
    )

    with patch("src.services.advisor_copilot_service.NotificationService", return_value=notification_service):
        result = service.run_stage("midday", send_notification=True)

    assert result["notification"]["success"] is True
    assert result["notification"]["channels"][0]["channel"] == "feishu"
    notification_service.send_with_results.assert_called_once()
