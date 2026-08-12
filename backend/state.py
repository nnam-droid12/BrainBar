"""In-memory shoot state — the single source of truth the REST endpoints and the
WebSocket stream both read from. Deliberately simple (no DB): a shooting day's state
fits comfortably in memory, and every mutation is also broadcast live.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from agents.schemas import ActionLog, DailiesPackage, RoutingDecision, TakeVerdict


@dataclass
class TakeRecord:
    take_id: str
    scene: str
    setup_id: str
    take_number: int
    start_timecode: str = "00:00:00:00"
    end_timecode: str = "00:00:00:00"
    start_time_utc: str = ""
    end_time_utc: str = ""
    verdict: TakeVerdict | None = None
    action_log: ActionLog | None = None
    routing: RoutingDecision | None = None
    rolling: bool = True
    error: str | None = None


@dataclass
class ShootState:
    scene: str = ""
    setup_id: str = ""
    take_number: int = 0
    takes: dict[str, TakeRecord] = field(default_factory=dict)
    take_order: list[str] = field(default_factory=list)
    coverage_owed: dict[str, list[str]] = field(default_factory=dict)  # scene -> owed types
    dailies: DailiesPackage | None = None
    active_incident: dict | None = None  # {node, grafana_incident_ref, opened_at}

    def start_take(self, take_id: str, scene: str, setup_id: str, take_number: int) -> None:
        self.scene = scene
        self.setup_id = setup_id
        self.take_number = take_number
        if take_id not in self.takes:
            self.take_order.append(take_id)
        self.takes[take_id] = TakeRecord(
            take_id=take_id, scene=scene, setup_id=setup_id, take_number=take_number
        )

    def set_verdict(
        self,
        take_id: str,
        verdict: TakeVerdict,
        start_timecode: str = "",
        end_timecode: str = "",
        start_time_utc: str = "",
        end_time_utc: str = "",
    ) -> None:
        record = self.takes.setdefault(
            take_id,
            TakeRecord(
                take_id=take_id,
                scene=verdict.scene,
                setup_id=verdict.setup_id,
                take_number=verdict.take_number,
            ),
        )
        record.verdict = verdict
        record.rolling = False
        if start_timecode:
            record.start_timecode = start_timecode
        if end_timecode:
            record.end_timecode = end_timecode
        if start_time_utc:
            record.start_time_utc = start_time_utc
        if end_time_utc:
            record.end_time_utc = end_time_utc
        self.coverage_owed[verdict.scene] = verdict.creative.coverage_owed

    def set_error(self, take_id: str, message: str) -> None:
        """Marks a take's pipeline as terminally failed (e.g. Vertex AI quota
        exhausted every retry) so it stops looking like it's still being analyzed —
        without this, a failed take sits at rolling=false/verdict=None forever, which
        the frontend can't distinguish from "still processing"."""
        if take_id in self.takes:
            record = self.takes[take_id]
            record.error = message
            record.rolling = False

    def set_action_log(self, take_id: str, action_log: ActionLog) -> None:
        if take_id in self.takes:
            self.takes[take_id].action_log = action_log

    def set_routing(self, take_id: str, routing: RoutingDecision) -> None:
        if take_id in self.takes:
            self.takes[take_id].routing = routing

    def set_dailies(self, dailies: DailiesPackage) -> None:
        self.dailies = dailies

    def to_dict(self) -> dict:
        return {
            "scene": self.scene,
            "setup_id": self.setup_id,
            "take_number": self.take_number,
            "takes": [
                {
                    "take_id": r.take_id,
                    "scene": r.scene,
                    "setup_id": r.setup_id,
                    "take_number": r.take_number,
                    "start_timecode": r.start_timecode,
                    "end_timecode": r.end_timecode,
                    "start_time_utc": r.start_time_utc,
                    "end_time_utc": r.end_time_utc,
                    "rolling": r.rolling,
                    "error": r.error,
                    "verdict": r.verdict.model_dump(mode="json") if r.verdict else None,
                    "action_log": r.action_log.model_dump(mode="json") if r.action_log else None,
                    "routing": r.routing.model_dump(mode="json") if r.routing else None,
                }
                for r in (self.takes[tid] for tid in self.take_order)
            ],
            "coverage_owed": self.coverage_owed,
            "dailies": self.dailies.model_dump(mode="json") if self.dailies else None,
            "active_incident": self.active_incident,
        }


state = ShootState()
