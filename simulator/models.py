"""Data model for the shoot script and in-flight take state."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Cue:
    frame_number: int
    type: str  # dolly | pyro | lighting


@dataclass(frozen=True)
class Setup:
    id: str
    description: str
    lens_mm: int
    movement: str
    framing: str
    coverage_type: str
    planned_takes: int
    cues: list[Cue] = field(default_factory=list)


@dataclass(frozen=True)
class ShootScript:
    scene: str
    scene_title: str
    int_ext: str
    time_of_day: str
    location: str
    setups: list[Setup]

    def setup(self, setup_id: str) -> Setup:
        for setup in self.setups:
            if setup.id == setup_id:
                return setup
        raise KeyError(f"unknown setup id: {setup_id}")


def load_shoot_script(path: str) -> ShootScript:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    setups = [
        Setup(
            id=s["id"],
            description=s["description"],
            lens_mm=s["lens_mm"],
            movement=s["movement"],
            framing=s["framing"],
            coverage_type=s["coverage_type"],
            planned_takes=s["planned_takes"],
            cues=[Cue(**c) for c in s.get("cues", [])],
        )
        for s in raw["setups"]
    ]
    return ShootScript(
        scene=raw["scene"],
        scene_title=raw["scene_title"],
        int_ext=raw["int_ext"],
        time_of_day=raw["time_of_day"],
        location=raw["location"],
        setups=setups,
    )


@dataclass
class TakeState:
    """Runtime state for one in-progress or completed take."""

    take_id: str
    scene: str
    setup_id: str
    take_number: int
    frame_number: int = 0
    rolling: bool = False
    start_timecode: str = ""
    end_timecode: str = ""
    fault: str | None = None
    node_offline: set[str] = field(default_factory=set)
