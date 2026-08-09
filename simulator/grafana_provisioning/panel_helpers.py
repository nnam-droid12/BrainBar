"""Small helpers for building Grafana dashboard JSON without a giant hand-written blob."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GridCursor:
    """Lays out panels left-to-right in rows on Grafana's 24-column grid."""

    col: int = 0
    row: int = 0
    row_height: int = 8

    def place(self, width: int, height: int | None = None) -> dict:
        height = height or self.row_height
        if self.col + width > 24:
            self.col = 0
            self.row += self.row_height
        pos = {"x": self.col, "y": self.row, "w": width, "h": height}
        self.col += width
        return pos


_next_id = [1]


def _id() -> int:
    _next_id[0] += 1
    return _next_id[0]


def timeseries_panel(
    title: str, prom_uid: str, exprs: list[tuple[str, str]], grid: dict, unit: str = "short",
    thresholds: list[dict] | None = None,
) -> dict:
    """exprs: list of (promql_expression, legend_format)."""
    return {
        "id": _id(),
        "type": "timeseries",
        "title": title,
        "gridPos": grid,
        "datasource": {"type": "prometheus", "uid": prom_uid},
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "thresholds": {
                    "mode": "absolute",
                    "steps": thresholds or [{"color": "green", "value": None}],
                },
            },
            "overrides": [],
        },
        "options": {"legend": {"displayMode": "list", "placement": "bottom"}},
        "targets": [
            {"expr": expr, "legendFormat": legend, "refId": chr(65 + i)}
            for i, (expr, legend) in enumerate(exprs)
        ],
    }


def stat_panel(title: str, prom_uid: str, expr: str, grid: dict, unit: str = "short",
                thresholds: list[dict] | None = None) -> dict:
    return {
        "id": _id(),
        "type": "stat",
        "title": title,
        "gridPos": grid,
        "datasource": {"type": "prometheus", "uid": prom_uid},
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "thresholds": {
                    "mode": "absolute",
                    "steps": thresholds or [{"color": "green", "value": None}],
                },
            },
            "overrides": [],
        },
        "targets": [{"expr": expr, "refId": "A"}],
    }


def logs_panel(title: str, loki_uid: str, expr: str, grid: dict) -> dict:
    return {
        "id": _id(),
        "type": "logs",
        "title": title,
        "gridPos": grid,
        "datasource": {"type": "loki", "uid": loki_uid},
        "options": {"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending"},
        "targets": [{"expr": expr, "refId": "A"}],
    }


def table_panel(title: str, tempo_uid: str, query: str, grid: dict, query_type: str = "traceql") -> dict:
    return {
        "id": _id(),
        "type": "table",
        "title": title,
        "gridPos": grid,
        "datasource": {"type": "tempo", "uid": tempo_uid},
        "targets": [{"query": query, "queryType": query_type, "refId": "A"}],
    }
