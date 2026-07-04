# -*- coding: utf-8 -*-
"""AI advisor copilot API endpoints."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.v1.schemas.common import ErrorResponse
from src.services.advisor_copilot_service import AdvisorCopilotService

logger = logging.getLogger(__name__)
router = APIRouter()


class AdvisorStageItem(BaseModel):
    id: str
    name: str
    time: str
    objective: str
    push_policy: str


class AdvisorSnapshotItem(BaseModel):
    id: str
    stage: str
    stage_name: str
    generated_at: str
    title: str
    action_level: str
    market_mode: str
    primary_theme: str
    summary: str
    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    watchpoints: List[str] = Field(default_factory=list)
    risk_controls: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    markdown: str = ""
    notification: Optional[Dict[str, Any]] = None


class AdvisorStatusResponse(BaseModel):
    enabled: bool
    mode: str
    notification_ready: bool
    notification_channels: List[str] = Field(default_factory=list)
    stages: List[AdvisorStageItem] = Field(default_factory=list)
    next_stage: AdvisorStageItem
    latest_snapshot: Optional[AdvisorSnapshotItem] = None


class AdvisorSnapshotListResponse(BaseModel):
    items: List[AdvisorSnapshotItem] = Field(default_factory=list)


class AdvisorRunRequest(BaseModel):
    stage: str = Field("auto", description="auction/open_confirm/midday/tail_risk/close_review/auto")
    send_notification: bool = False


class AdvisorRunResponse(BaseModel):
    snapshot: AdvisorSnapshotItem
    notification: Optional[Dict[str, Any]] = None


def get_advisor_service() -> AdvisorCopilotService:
    return AdvisorCopilotService()


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail={"error": "validation_error", "message": str(exc)})


def _internal_error(message: str, exc: Exception) -> HTTPException:
    logger.error("%s: %s", message, exc, exc_info=True)
    return HTTPException(status_code=500, detail={"error": "internal_error", "message": message})


@router.get(
    "/status",
    response_model=AdvisorStatusResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Get advisor copilot status",
)
def get_status() -> AdvisorStatusResponse:
    try:
        return AdvisorStatusResponse(**get_advisor_service().get_status())
    except Exception as exc:
        raise _internal_error("Load advisor status failed", exc)


@router.get(
    "/snapshots",
    response_model=AdvisorSnapshotListResponse,
    responses={500: {"model": ErrorResponse}},
    summary="List advisor copilot snapshots",
)
def list_snapshots(limit: int = Query(20, ge=1, le=100)) -> AdvisorSnapshotListResponse:
    try:
        return AdvisorSnapshotListResponse(items=get_advisor_service().list_snapshots(limit=limit))
    except Exception as exc:
        raise _internal_error("List advisor snapshots failed", exc)


@router.post(
    "/run",
    response_model=AdvisorRunResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Run one advisor copilot stage",
)
def run_stage(request: AdvisorRunRequest) -> AdvisorRunResponse:
    try:
        return AdvisorRunResponse(**get_advisor_service().run_stage(
            request.stage,
            send_notification=request.send_notification,
        ))
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Run advisor stage failed", exc)


@router.post(
    "/notify-test",
    response_model=AdvisorRunResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Send latest advisor snapshot to notification channels",
)
def notify_test() -> AdvisorRunResponse:
    try:
        return AdvisorRunResponse(**get_advisor_service().send_latest_or_sample())
    except Exception as exc:
        raise _internal_error("Advisor notification test failed", exc)
