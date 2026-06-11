from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
)


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "helios-dataset-outreach.md"
OUTPUT = ROOT / "helios-dataset-outreach.pdf"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#12312B"),
            spaceAfter=18,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=20,
            textColor=colors.HexColor("#12312B"),
            spaceBefore=14,
            spaceAfter=7,
        ),
        "h3": ParagraphStyle(
            "Heading3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#315B4F"),
            spaceBefore=10,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.2,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#202A27"),
            spaceAfter=6,
        ),
        "label": ParagraphStyle(
            "Label",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#12312B"),
            spaceBefore=3,
            spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12.5,
            leftIndent=12,
            textColor=colors.HexColor("#202A27"),
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.5,
            leading=10,
            backColor=colors.HexColor("#F4F6F3"),
            borderColor=colors.HexColor("#D7DDD7"),
            borderWidth=0.5,
            borderPadding=6,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "email": ParagraphStyle(
            "Email",
            parent=base["Code"],
            fontName="Courier",
            fontSize=8.2,
            leading=11.2,
            backColor=colors.HexColor("#F8FAF7"),
            borderColor=colors.HexColor("#C9D5CC"),
            borderWidth=0.75,
            borderPadding=8,
            spaceBefore=6,
            spaceAfter=8,
        ),
    }


def _clean_inline(text: str) -> str:
    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return escaped.replace("`", "")


def _page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D7DDD7"))
    canvas.line(doc.leftMargin, 0.68 * inch, LETTER[0] - doc.rightMargin, 0.68 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#66736D"))
    canvas.drawString(doc.leftMargin, 0.45 * inch, "Irrigant Helios dataset outreach guide")
    canvas.drawRightString(LETTER[0] - doc.rightMargin, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _flush_list(items: list[str], story: list, style: ParagraphStyle) -> None:
    if not items:
        return
    story.append(
        ListFlowable(
            [ListItem(Paragraph(_clean_inline(item), style)) for item in items],
            bulletType="bullet",
            start="circle",
            leftIndent=18,
            bulletFontSize=6,
            bulletOffsetY=1,
            spaceAfter=6,
        )
    )
    items.clear()


def build_story(markdown: str) -> list:
    styles = _styles()
    story: list = []
    bullet_items: list[str] = []
    email_lines: list[str] = []
    in_email = False

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line == "Subject: Data partnership request to improve Helios irrigation accuracy":
            _flush_list(bullet_items, story, styles["bullet"])
            in_email = True
            email_lines.append(line)
            continue
        if line == "## Follow-Up Questions for a Call" and in_email:
            story.append(Preformatted("\n".join(email_lines), styles["email"]))
            email_lines.clear()
            in_email = False

        if in_email:
            email_lines.append(line)
            continue

        if not line:
            _flush_list(bullet_items, story, styles["bullet"])
            story.append(Spacer(1, 3))
            continue
        if line.startswith("# "):
            _flush_list(bullet_items, story, styles["bullet"])
            story.append(Paragraph(_clean_inline(line[2:]), styles["title"]))
            continue
        if line.startswith("## "):
            _flush_list(bullet_items, story, styles["bullet"])
            story.append(Paragraph(_clean_inline(line[3:]), styles["h2"]))
            continue
        if line.startswith("### "):
            _flush_list(bullet_items, story, styles["bullet"])
            story.append(Paragraph(_clean_inline(line[4:]), styles["h3"]))
            continue
        if line.startswith("- "):
            bullet_items.append(line[2:])
            continue
        if line.startswith("Ask for:") or line.startswith("Why it matters:"):
            _flush_list(bullet_items, story, styles["bullet"])
            story.append(Paragraph(_clean_inline(line), styles["label"]))
            continue
        if line.startswith("`") and line.endswith("`"):
            _flush_list(bullet_items, story, styles["bullet"])
            story.append(Preformatted(line.strip("`"), styles["code"]))
            continue

        _flush_list(bullet_items, story, styles["bullet"])
        story.append(Paragraph(_clean_inline(line), styles["body"]))

    _flush_list(bullet_items, story, styles["bullet"])
    if email_lines:
        story.append(Preformatted("\n".join(email_lines), styles["email"]))
    return story


def main() -> None:
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=LETTER,
        leftMargin=0.72 * inch,
        rightMargin=0.72 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.82 * inch,
        title="Helios Dataset Outreach Guide",
        author="Irrigant Helios",
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="normal",
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_page)])
    story = build_story(SOURCE.read_text(encoding="utf-8"))
    story.insert(
        1,
        Paragraph(
            "A practical partner outreach asset for collecting data that improves Helios recommendation accuracy.",
            _styles()["body"],
        ),
    )
    doc.build([KeepTogether(story[:3]), *story[3:]])
    print(OUTPUT)


if __name__ == "__main__":
    main()
