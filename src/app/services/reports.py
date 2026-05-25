from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO
from pathlib import Path

from ..database import CheckHistoryRecord


def generate_pdf_report(record: CheckHistoryRecord) -> bytes:
    return _generate_reportlab_pdf(record)


def _generate_reportlab_pdf(record: CheckHistoryRecord) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font_name = _register_cyrillic_font()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        leading=22,
        spaceAfter=10,
    )
    normal_style = ParagraphStyle(
        "ReportNormal",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=10,
        leading=14,
    )
    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=13,
        leading=16,
        spaceBefore=12,
        spaceAfter=6,
    )

    result = record.result
    story = [
        Paragraph("Отчет о проверке документа", title_style),
        _metadata_table(record, normal_style, font_name),
        Spacer(1, 8),
        Paragraph("Краткое заключение", heading_style),
        Paragraph(_escape(result.get("summary") or "Заключение не указано."), normal_style),
        Paragraph("Найденные ошибки", heading_style),
    ]

    errors = result.get("errors") or []
    if not errors:
        story.append(Paragraph("Ошибок не найдено.", normal_style))
    else:
        rows = [["Раздел", "Тип", "Критичность", "Описание"]]
        for error in errors:
            rows.append(
                [
                    Paragraph(_escape(error.get("section") or "Общий документ"), normal_style),
                    Paragraph(_escape(error.get("error_type") or ""), normal_style),
                    Paragraph(_escape(error.get("severity") or ""), normal_style),
                    Paragraph(_escape(error.get("description") or ""), normal_style),
                ]
            )

        table = Table(rows, colWidths=[36 * mm, 30 * mm, 28 * mm, 70 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(table)

    doc.build(story)
    return buffer.getvalue()


def _metadata_table(record: CheckHistoryRecord, style, font_name: str) -> object:
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

    rows = [
        ["Пользователь", record.user_email],
        ["Документ", record.document_name],
        ["Шаблон", record.template_name or "Загруженный вручную"],
        ["Модель", record.model_id],
        ["Дата проверки", _format_datetime(record.created_at)],
        ["Оценка соответствия", f"{record.compliance_score}%"],
        ["Ошибок", str(record.errors_count)],
    ]
    table = Table(
        [[Paragraph(_escape(str(cell)), style) for cell in row] for row in rows],
        colWidths=[42 * mm, 122 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _register_cyrillic_font() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_path = _find_cyrillic_font()
    font_name = "DocumentCheckerCyrillic"
    if font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
    return font_name


def _find_cyrillic_font() -> Path:
    configured = os.getenv("PDF_FONT_PATH")
    candidates = [
        Path(configured) if configured else None,
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/times.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
        Path("/usr/local/share/fonts/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path and path.exists():
            return path
    raise RuntimeError(
        "No TrueType font with Cyrillic support found. "
        "Install DejaVu/Noto fonts or set PDF_FONT_PATH."
    )


def _format_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
