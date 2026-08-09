"""SMPTE non-drop timecode helpers, HH:MM:SS:FF."""
from __future__ import annotations


def frames_to_timecode(total_frames: int, fps: int) -> str:
    hours, rem = divmod(total_frames, fps * 3600)
    minutes, rem = divmod(rem, fps * 60)
    seconds, frames = divmod(rem, fps)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
