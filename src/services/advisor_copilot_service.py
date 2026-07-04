# -*- coding: utf-8 -*-
"""AI advisor copilot MVP service.

The first version is intentionally conservative: it builds a structured
watch-room snapshot, persists it locally, and can route the snapshot through the
existing notification service. It does not place trades or auto-execute orders.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import get_config
from src.notification import NotificationService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AdvisorStage:
    id: str
    name: str
    time: str
    objective: str
    push_policy: str


@dataclass
class AdvisorSnapshot:
    id: str
    stage: str
    stage_name: str
    generated_at: str
    title: str
    action_level: str
    market_mode: str
    primary_theme: str
    summary: str
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    watchpoints: List[str] = field(default_factory=list)
    risk_controls: List[str] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)
    markdown: str = ""
    notification: Optional[Dict[str, Any]] = None


DEFAULT_STAGES: List[AdvisorStage] = [
    AdvisorStage(
        id="auction",
        name="竞价题材雷达",
        time="09:20",
        objective="识别隔夜催化、竞价异动、疑似启动题材和需要回避的一日游方向。",
        push_policy="只推送题材强度、核心锚点和开盘确认条件，不给无条件买入指令。",
    ),
    AdvisorStage(
        id="open_confirm",
        name="开盘主线确认",
        time="10:00",
        objective="判断题材是真启动、短暂拉升还是资金试探，分层龙头/中军/补涨。",
        push_policy="仅当主线强度提升、候选股出现可观察买点或风险证伪时推送。",
    ),
    AdvisorStage(
        id="midday",
        name="午盘策略校准",
        time="11:30",
        objective="复核上午主线持续性、量价承接、持仓风险和下午观察点。",
        push_policy="推送仓位上限、下午跟踪条件和需要撤退的证伪信号。",
    ),
    AdvisorStage(
        id="tail_risk",
        name="尾盘风控",
        time="14:30",
        objective="检查高位分歧、尾盘抢筹、隔夜风险和是否需要降仓。",
        push_policy="优先推风险控制，只有高确定性延续信号才提示隔夜观察。",
    ),
    AdvisorStage(
        id="close_review",
        name="收盘复盘",
        time="15:30",
        objective="沉淀今日主线、情绪周期、候选池变化和明日交易计划。",
        push_policy="形成明日观察清单和纪律清单，作为下一交易日竞价输入。",
    ),
]


class AdvisorCopilotService:
    """Build, persist, and notify AI advisor watch-room snapshots."""

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        self.storage_path = storage_path or Path("data") / "advisor_copilot_snapshots.json"

    def get_status(self) -> Dict[str, Any]:
        latest = self.latest_snapshot()
        channels = [
            channel.value
            for channel in NotificationService.detect_configured_channels(get_config())
        ]
        return {
            "enabled": True,
            "mode": "advisor_copilot_mvp",
            "notification_ready": bool(channels),
            "notification_channels": channels,
            "stages": [asdict(stage) for stage in DEFAULT_STAGES],
            "next_stage": asdict(self._guess_current_stage()),
            "latest_snapshot": asdict(latest) if latest else None,
        }

    def list_snapshots(self, limit: int = 20) -> List[Dict[str, Any]]:
        snapshots = self._load_snapshots()
        return [asdict(item) for item in snapshots[: max(1, min(limit, 100))]]

    def run_stage(self, stage_id: str = "auto", *, send_notification: bool = False) -> Dict[str, Any]:
        stage = self._resolve_stage(stage_id)
        snapshot = self._build_snapshot(stage)
        if send_notification:
            snapshot.notification = self._send_snapshot_notification(snapshot, route_type="report")
        self._prepend_snapshot(snapshot)
        return {
            "snapshot": asdict(snapshot),
            "notification": snapshot.notification,
        }

    def send_latest_or_sample(self) -> Dict[str, Any]:
        snapshot = self.latest_snapshot() or self._build_snapshot(self._guess_current_stage())
        result = self._send_snapshot_notification(snapshot, route_type="system_error")
        snapshot.notification = result
        self._prepend_snapshot(snapshot)
        return {
            "snapshot": asdict(snapshot),
            "notification": result,
        }

    def latest_snapshot(self) -> Optional[AdvisorSnapshot]:
        snapshots = self._load_snapshots()
        return snapshots[0] if snapshots else None

    def _resolve_stage(self, stage_id: str) -> AdvisorStage:
        if not stage_id or stage_id == "auto":
            return self._guess_current_stage()
        for stage in DEFAULT_STAGES:
            if stage.id == stage_id:
                return stage
        raise ValueError(f"Unknown advisor stage: {stage_id}")

    def _guess_current_stage(self) -> AdvisorStage:
        now = datetime.now().time()
        if now < time(9, 45):
            return DEFAULT_STAGES[0]
        if now < time(11, 0):
            return DEFAULT_STAGES[1]
        if now < time(13, 30):
            return DEFAULT_STAGES[2]
        if now < time(15, 0):
            return DEFAULT_STAGES[3]
        return DEFAULT_STAGES[4]

    def _build_snapshot(self, stage: AdvisorStage) -> AdvisorSnapshot:
        generated_at = datetime.now().isoformat(timespec="seconds")
        title = f"{stage.name} - AI投顾值班快照"
        action_level = self._stage_action_level(stage.id)
        market_mode = self._stage_market_mode(stage.id)
        primary_theme = "等待数据确认的当日主线"
        candidates = self._default_candidates(stage.id)
        watchpoints = self._default_watchpoints(stage.id)
        risk_controls = self._default_risk_controls(stage.id)
        next_actions = self._default_next_actions(stage.id)
        summary = (
            f"{stage.name}已生成。当前版本聚焦题材生命周期、量价确认、龙头分层和交易纪律；"
            "结论作为决策辅助，不构成自动交易或收益承诺。"
        )
        snapshot = AdvisorSnapshot(
            id=str(uuid.uuid4()),
            stage=stage.id,
            stage_name=stage.name,
            generated_at=generated_at,
            title=title,
            action_level=action_level,
            market_mode=market_mode,
            primary_theme=primary_theme,
            summary=summary,
            candidates=candidates,
            watchpoints=watchpoints,
            risk_controls=risk_controls,
            next_actions=next_actions,
        )
        snapshot.markdown = self._format_markdown(snapshot, stage)
        return snapshot

    @staticmethod
    def _stage_action_level(stage_id: str) -> str:
        mapping = {
            "auction": "观察",
            "open_confirm": "条件参与",
            "midday": "校准仓位",
            "tail_risk": "风控优先",
            "close_review": "制定计划",
        }
        return mapping.get(stage_id, "观察")

    @staticmethod
    def _stage_market_mode(stage_id: str) -> str:
        mapping = {
            "auction": "待确认",
            "open_confirm": "确认主线",
            "midday": "分歧检验",
            "tail_risk": "隔夜风险",
            "close_review": "复盘沉淀",
        }
        return mapping.get(stage_id, "待确认")

    @staticmethod
    def _default_candidates(stage_id: str) -> List[Dict[str, Any]]:
        base = [
            {
                "type": "龙头",
                "status": "等待确认",
                "rule": "题材内最先启动、最强封单或最强趋势承接，优先于后排跟风。",
            },
            {
                "type": "容量中军",
                "status": "观察承接",
                "rule": "成交额放大但不失控，回踩 VWAP/MA5 不破时才进入候选。",
            },
            {
                "type": "补涨",
                "status": "低仓试错",
                "rule": "只在主线已确认且龙头继续强化时考虑，禁止高潮日追后排。",
            },
        ]
        if stage_id in {"tail_risk", "close_review"}:
            base.append({
                "type": "禁止池",
                "status": "默认回避",
                "rule": "高位放量长上影、炸板无回封、后排一致转分歧的标的优先剔除。",
            })
        return base

    @staticmethod
    def _default_watchpoints(stage_id: str) -> List[str]:
        common = [
            "板块是否连续强于指数，成交额是否向主线集中。",
            "龙头是否带动中军和补涨，而不是只有单票脉冲。",
            "量价是否匹配：放量突破、缩量回踩、VWAP 承接优先；放量下跌降级。",
        ]
        stage_extra = {
            "auction": ["竞价强度能否延续到开盘后 15 分钟。"],
            "open_confirm": ["开盘分歧后资金是否回流核心票。"],
            "midday": ["上午强势题材下午是否继续扩散，还是转为一日游。"],
            "tail_risk": ["尾盘是否出现抢筹失败、炸板扩散或核心股漏单。"],
            "close_review": ["明日只跟踪能被今日数据验证的方向。"],
        }
        return common + stage_extra.get(stage_id, [])

    @staticmethod
    def _default_risk_controls(stage_id: str) -> List[str]:
        controls = [
            "不因单条新闻或社媒热度直接追高，必须有板块强度和量价确认。",
            "T+1 下当日买入不可卖出，仓位要按最坏情况预留回撤空间。",
            "若龙头断板无修复、板块涨停家数快速收缩，候选池整体降级。",
        ]
        if stage_id == "tail_risk":
            controls.insert(0, "尾盘阶段优先处理风险，不为追隔夜溢价扩大仓位。")
        return controls

    @staticmethod
    def _default_next_actions(stage_id: str) -> List[str]:
        mapping = {
            "auction": [
                "开盘后确认竞价异动方向是否继续放量。",
                "只记录疑似主线和核心锚点，等待 10:00 二次确认。",
            ],
            "open_confirm": [
                "把确认主线拆成龙头、中军、补涨、禁止池。",
                "对候选股执行八维+紫苏叶+缠论组合复核。",
            ],
            "midday": [
                "更新下午观察点和仓位上限。",
                "对走弱题材设置证伪提醒。",
            ],
            "tail_risk": [
                "检查持仓是否触发止盈、止损或降仓条件。",
                "避免新开后排，优先留下次日可验证计划。",
            ],
            "close_review": [
                "沉淀明日观察清单。",
                "记录今天信号被强化、削弱或证伪的原因。",
            ],
        }
        return mapping.get(stage_id, ["等待下一阶段确认。"])

    def _format_markdown(self, snapshot: AdvisorSnapshot, stage: AdvisorStage) -> str:
        lines = [
            f"# {snapshot.title}",
            "",
            f"- 生成时间：{snapshot.generated_at}",
            f"- 当前阶段：{snapshot.stage_name}",
            f"- 行动级别：{snapshot.action_level}",
            f"- 市场模式：{snapshot.market_mode}",
            "",
            "## 阶段目标",
            stage.objective,
            "",
            "## 当前结论",
            snapshot.summary,
            "",
            "## 观察候选分层",
        ]
        for item in snapshot.candidates:
            lines.append(f"- {item['type']}：{item['status']}。{item['rule']}")
        lines.extend(["", "## 关键观察点"])
        lines.extend(f"- {item}" for item in snapshot.watchpoints)
        lines.extend(["", "## 风控纪律"])
        lines.extend(f"- {item}" for item in snapshot.risk_controls)
        lines.extend(["", "## 下一步"])
        lines.extend(f"- {item}" for item in snapshot.next_actions)
        lines.extend([
            "",
            "## 免责声明",
            "本快照仅用于研究和交易纪律辅助，不构成投资建议，不承诺收益；最终交易由用户自行确认。",
        ])
        return "\n".join(lines)

    def _send_snapshot_notification(self, snapshot: AdvisorSnapshot, *, route_type: str) -> Dict[str, Any]:
        try:
            result = NotificationService().send_with_results(
                snapshot.markdown,
                route_type=route_type,
                severity="info",
                dedup_key=f"advisor:{snapshot.stage}:{snapshot.generated_at[:10]}:{snapshot.id}",
            )
        except Exception as exc:  # noqa: BLE001 - notification failures must be observable, not fatal.
            logger.exception("Advisor copilot notification failed: %s", exc)
            return {
                "success": False,
                "status": "exception",
                "message": str(exc),
                "channels": [],
            }
        return {
            "success": result.success,
            "status": result.status,
            "message": result.message,
            "channels": [
                {
                    "channel": item.channel,
                    "success": item.success,
                    "error_code": item.error_code,
                    "latency_ms": item.latency_ms,
                }
                for item in result.channel_results
            ],
        }

    def _load_snapshots(self) -> List[AdvisorSnapshot]:
        if not self.storage_path.exists():
            return []
        try:
            raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load advisor snapshots: %s", exc)
            return []
        items = raw if isinstance(raw, list) else []
        snapshots: List[AdvisorSnapshot] = []
        for item in items:
            if isinstance(item, dict):
                try:
                    snapshots.append(AdvisorSnapshot(**item))
                except TypeError:
                    continue
        return snapshots

    def _prepend_snapshot(self, snapshot: AdvisorSnapshot) -> None:
        snapshots = [snapshot] + [
            item for item in self._load_snapshots()
            if item.id != snapshot.id
        ]
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(item) for item in snapshots[:100]]
        self.storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
