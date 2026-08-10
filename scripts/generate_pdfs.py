"""Generates the script and call-sheet PDFs in assets/ from the plain-text/structured
source content. Re-run after editing assets/script/scene.txt or the call sheet fields
below: `python -m scripts.generate_pdfs`

These PDFs are what agents/continuity/ingest.py feeds to Document AI — real documents
for a real parsing step, not synthetic structured data pretending to be a PDF.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_TXT = ROOT / "assets" / "script" / "scene.txt"
SCRIPT_PDF = ROOT / "assets" / "script" / "scene.pdf"
CALL_SHEET_PDF = ROOT / "assets" / "call-sheet" / "call_sheet.pdf"

styles = getSampleStyleSheet()
SLUG = ParagraphStyle("Slug", parent=styles["Heading2"], fontName="Courier-Bold")
ACTION = ParagraphStyle("Action", parent=styles["Normal"], fontName="Courier", leading=14)
DIALOGUE_NAME = ParagraphStyle(
    "DialogueName", parent=styles["Normal"], fontName="Courier-Bold",
    leftIndent=2.0 * inch, spaceBefore=8,
)
DIALOGUE = ParagraphStyle(
    "Dialogue", parent=styles["Normal"], fontName="Courier",
    leftIndent=1.3 * inch, rightIndent=1.3 * inch, leading=14,
)


def build_script_pdf() -> None:
    doc = SimpleDocTemplate(str(SCRIPT_PDF), pagesize=LETTER)
    story: list = []
    lines = SCRIPT_TXT.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 8))
        elif stripped.startswith("SC") and ("INT." in stripped or "EXT." in stripped):
            story.append(Paragraph(stripped, SLUG))
        elif stripped.isupper() and len(stripped.split()) <= 4 and not stripped.startswith("("):
            story.append(Paragraph(stripped, DIALOGUE_NAME))
        elif stripped.startswith("(") or stripped.startswith("CUT TO"):
            story.append(Paragraph(stripped, DIALOGUE))
        elif line.startswith(" " * 10):
            story.append(Paragraph(stripped, DIALOGUE))
        else:
            story.append(Paragraph(stripped, ACTION))
        i += 1
    doc.build(story)


CALL_TIMES = [
    ["Name", "Role", "Call Time", "Notes"],
    ["Mara Voss (actor)", "Cast — Mara", "5:00 PM", "Hair/makeup 4:00 PM"],
    ["Deacon Reyes (actor)", "Cast — Deacon", "5:00 PM", "Hair/makeup 4:00 PM"],
    ["Volume Supervisor", "Technical", "3:00 PM", "Render cluster preflight"],
    ["DP", "Camera", "4:00 PM", "Lens/tracking calibration"],
    ["1st AD", "AD Dept.", "3:00 PM", "Runs BrainBar circle-take review"],
    ["VFX Supervisor", "VFX", "4:30 PM", "On call for clean-plate review"],
]

SCHEDULE = [
    ["Scene", "Setup", "Description", "Est. Time"],
    ["SC03", "1", "Wide master — dolly push, train pass, pyro cue", "6:00 PM"],
    ["SC03", "2", "Single on Mara — handheld push", "7:00 PM"],
    ["SC03", "3", "Reverse single on Deacon — static", "7:45 PM"],
    ["SC03", "4", "Clean plate — wall only", "8:15 PM"],
]


def _table(data: list[list[str]]) -> Table:
    t = Table(data, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1c1f26")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def build_call_sheet_pdf() -> None:
    doc = SimpleDocTemplate(str(CALL_SHEET_PDF), pagesize=LETTER)
    story = [
        Paragraph("BrainBar Pictures — Daily Call Sheet", styles["Title"]),
        Paragraph("Production: PLATFORM STANDOFF — Shoot Day 4 of 12", styles["Heading3"]),
        Paragraph(
            "Date: Thursday, March 12, 2026 &nbsp;&nbsp;|&nbsp;&nbsp; "
            "Location: LED Volume Stage B &nbsp;&nbsp;|&nbsp;&nbsp; "
            "General Call: 3:00 PM",
            styles["Normal"],
        ),
        Spacer(1, 16),
        Paragraph("Cast &amp; Crew Call Times", styles["Heading2"]),
        _table(CALL_TIMES),
        Spacer(1, 16),
        Paragraph("Scene Schedule", styles["Heading2"]),
        _table(SCHEDULE),
        Spacer(1, 16),
        Paragraph("Safety Notes", styles["Heading2"]),
        Paragraph(
            "Setup 1 includes a scripted pyro cue at frame 200 timed to the dolly push. "
            "Render cluster is monitored live by BrainBar; any HOLD/RESHOOT verdict will be "
            "announced by the 1st AD before the next take is called. Clean plate (setup 4) "
            "is required coverage for VFX and must not be skipped even if the day runs long.",
            styles["Normal"],
        ),
    ]
    doc.build(story)


if __name__ == "__main__":
    build_script_pdf()
    build_call_sheet_pdf()
    print(f"Wrote {SCRIPT_PDF}")
    print(f"Wrote {CALL_SHEET_PDF}")
