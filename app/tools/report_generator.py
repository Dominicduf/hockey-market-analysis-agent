import io
import logging
from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from langchain_core.tools import tool
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas import SentimentResult

matplotlib.use("Agg")

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _score_color(score: float) -> str:
    if score >= 0.3:
        return "#27ae60"
    elif score >= 0:
        return "#f39c12"
    return "#e74c3c"


def _build_bar_chart(results: list[SentimentResult]) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(7, 3.5))

    names = [r.product_name for r in results]
    scores = [r.overall_score for r in results]
    bar_colors = [_score_color(s) for s in scores]

    bars = ax.barh(names, scores, color=bar_colors, height=0.5, edgecolor="white")
    ax.set_xlim(-1, 1.2)
    ax.axvline(x=0, color="#2c3e50", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Sentiment Score", fontsize=9)
    ax.set_title("Overall Sentiment Score by Product", fontsize=11, fontweight="bold", pad=10)
    ax.tick_params(axis="y", labelsize=8)
    ax.tick_params(axis="x", labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bar, score in zip(bars, scores):
        x_pos = score + 0.04 if score >= 0 else score - 0.04
        ha = "left" if score >= 0 else "right"
        ax.text(
            x_pos,
            bar.get_y() + bar.get_height() / 2,
            f"{score:.2f}",
            va="center",
            ha=ha,
            fontsize=8,
            fontweight="bold",
            color=_score_color(score),
        )

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf


def _build_pdf(results: list[SentimentResult], output_path: Path) -> None:
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph("Hockey Equipment Market Analysis", styles["Title"]))
    elements.append(
        Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y')}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.15 * inch))

    # Bar chart
    chart_buf = _build_bar_chart(results)
    elements.append(Image(chart_buf, width=6.5 * inch, height=3.5 * inch))
    elements.append(Spacer(1, 0.15 * inch))

    # Summary table
    cell_style = ParagraphStyle(
        "cell",
        fontSize=8,
        leading=11,
        wordWrap="CJK",
    )
    header_style = ParagraphStyle(
        "header",
        fontSize=8,
        leading=11,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )

    def cell(text: str) -> Paragraph:
        return Paragraph(str(text), cell_style)

    def header_cell(text: str) -> Paragraph:
        return Paragraph(str(text), header_style)

    header = [
        header_cell(h)
        for h in ["Product", "Score", "Pos / Neu / Neg", "Top Praised", "Top Complaint"]
    ]
    rows = [header]
    for r in results:
        dist = r.sentiment_distribution
        dist_str = (
            f"{dist.get('positive', 0)} / {dist.get('neutral', 0)} / {dist.get('negative', 0)}"
        )
        rows.append(
            [
                cell(r.product_name),
                cell(f"{r.overall_score:.2f}"),
                cell(dist_str),
                cell(r.top_praised[0] if r.top_praised else "-"),
                cell(r.top_complaints[0] if r.top_complaints else "-"),
            ]
        )

    col_widths = [2.1 * inch, 0.55 * inch, 1.1 * inch, 1.5 * inch, 1.5 * inch]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 0), (2, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(table)

    doc.build(elements)


@tool
def generate_report(sentiment_results: list[str]) -> str:
    """
    Generate a one-page PDF market analysis report from sentiment analysis results.
    Must be called after analyze_sentiment has been called for all relevant products.
    Pass all analyze_sentiment JSON outputs together as a list in a single call.

    Args:
        sentiment_results: List of JSON strings returned by analyze_sentiment.

    Returns:
        The filename of the generated PDF report.
    """
    logger.info("[TOOL] generate_report called with %d result(s)", len(sentiment_results))

    try:
        results = [SentimentResult.model_validate_json(raw) for raw in sentiment_results]

        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = REPORTS_DIR / filename

        _build_pdf(results, output_path)

        logger.info("[TOOL] Report generated: %s", filename)
        return (
            f"Report successfully generated: {filename}. "
            f"The user can download it at GET /reports/{filename}"
        )

    except Exception as e:
        logger.error("[TOOL] Failed to generate report: %s", e)
        return (
            f"[TOOL ERROR] Failed to generate report: {e}. "
            "Do not infer or guess. Inform the user that report generation failed."
        )
