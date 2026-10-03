from html import escape
from pathlib import Path
from uuid import uuid4

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.schemas import CitedText, ResearchFinding, ResearchReport


class PDFServiceError(RuntimeError):
    pass


def _paragraph_text(text: str) -> str:
    return escape(text).replace("\n", "<br/>")


def _citation_label(source_ids: list[str]) -> str:
    if not source_ids:
        return ""
    return f" <font color='#52605e'>(Sources: {escape(', '.join(source_ids))})</font>"


def _cited_paragraph(text: CitedText, style: ParagraphStyle) -> Paragraph:
    content = _paragraph_text(text.text) + _citation_label(text.source_ids)
    return Paragraph(content, style)


def _finding_paragraph(finding: ResearchFinding, style: ParagraphStyle) -> Paragraph:
    content = _paragraph_text(finding.claim) + _citation_label(finding.source_ids)
    return Paragraph(content, style)


def generate_report_pdf(report: ResearchReport, output_dir: Path) -> str:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"research-report-{uuid4().hex[:12]}.pdf"
        output_path = output_dir / filename

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
            fontSize=22, leading=27, alignment=TA_CENTER, textColor=colors.HexColor("#173c36"),
            spaceAfter=18,
        ))
        styles.add(ParagraphStyle(
            name="ReportHeading", parent=styles["Heading2"], fontName="Helvetica-Bold",
            fontSize=14, leading=18, textColor=colors.HexColor("#173c36"),
            spaceBefore=14, spaceAfter=7, keepWithNext=True,
        ))
        styles.add(ParagraphStyle(
            name="ReportBody", parent=styles["BodyText"], fontName="Helvetica",
            fontSize=10, leading=15, textColor=colors.HexColor("#26312f"), spaceAfter=9,
        ))
        styles.add(ParagraphStyle(
            name="Reference", parent=styles["BodyText"], fontName="Helvetica",
            fontSize=8.5, leading=12, textColor=colors.HexColor("#26312f"), spaceAfter=7,
            wordWrap="CJK",
        ))

        def draw_page_number(canvas, document) -> None:
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor("#d9e1de"))
            canvas.line(0.75 * inch, 0.62 * inch, 7.75 * inch, 0.62 * inch)
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#52605e"))
            canvas.drawRightString(7.75 * inch, 0.42 * inch, f"Page {document.page}")
            canvas.restoreState()

        document = SimpleDocTemplate(
            str(output_path), pagesize=letter, rightMargin=0.8 * inch, leftMargin=0.8 * inch,
            topMargin=0.75 * inch, bottomMargin=0.85 * inch,
            title=report.title, author="Research Report Generator",
        )
        story = [Paragraph(_paragraph_text(report.title), styles["ReportTitle"])]
        story.extend([
            Paragraph("Executive Summary", styles["ReportHeading"]),
            _cited_paragraph(report.executive_summary, styles["ReportBody"]),
            Paragraph("Introduction", styles["ReportHeading"]),
            _cited_paragraph(report.introduction, styles["ReportBody"]),
        ])

        for section in report.sections:
            story.append(Paragraph(_paragraph_text(section.heading), styles["ReportHeading"]))
            story.append(_cited_paragraph(section.body, styles["ReportBody"]))

        story.append(Paragraph("Key Findings", styles["ReportHeading"]))
        for finding in report.key_findings:
            story.append(_finding_paragraph(finding, styles["ReportBody"]))

        story.extend([
            Paragraph("Conclusion", styles["ReportHeading"]),
            _cited_paragraph(report.conclusion, styles["ReportBody"]),
            Paragraph("References", styles["ReportHeading"]),
        ])
        for reference in report.references:
            safe_title = _paragraph_text(reference.title)
            safe_url = escape(str(reference.url), quote=True)
            story.append(Paragraph(
                f"[{escape(reference.source_id)}] <link href=\"{safe_url}\" color=\"#146b5a\">"
                f"{safe_title}</link><br/><font size=8>{safe_url}</font>",
                styles["Reference"],
            ))

        document.build(story, onFirstPage=draw_page_number, onLaterPages=draw_page_number)
        return filename
    except Exception as exc:
        raise PDFServiceError("The PDF report could not be generated.") from exc
