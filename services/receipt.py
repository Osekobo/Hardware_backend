from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

STORE_NAME = "Kione Hardware"
STORE_TAGLINE = "Building Trust, Building Kenya"
CURRENCY = "KSh"


def _fmt_money(value):
    return f"{CURRENCY} {value:,.2f}"


def _fmt_date(value):
    if not value:
        return "-"
    return value.strftime("%d %b %Y, %H:%M")


def generate_order_receipt_pdf(order, items, user):
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=f"Receipt - Order #{order.id}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=2,
    )
    tagline_style = ParagraphStyle(
        "Tagline",
        parent=styles["Normal"],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#6b7280"),
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#1f2937"),
        spaceBefore=10,
        spaceAfter=4,
    )
    right_style = ParagraphStyle(
        "Right", parent=styles["Normal"], fontSize=10, alignment=TA_RIGHT
    )
    small_style = ParagraphStyle(
        "Small", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#4b5563")
    )

    story = []

    story.append(Paragraph(STORE_NAME, title_style))
    story.append(Paragraph(STORE_TAGLINE, tagline_style))
    story.append(Spacer(1, 6 * mm))

    header_rows = [
        [
            Paragraph(
                f"<b>Order #{order.id}</b><br/>"
                f"Status: <b>{order.status.upper()}</b>",
                styles["Normal"],
            ),
            Paragraph(
                f"<b>Date:</b> {_fmt_date(order.created_at)}<br/>"
                f"<b>Paid:</b> {_fmt_date(order.paid_at) if order.status == 'paid' else '-'}",
                right_style,
            ),
        ]
    ]
    header = Table(header_rows, colWidths=[doc.width / 2.0] * 2)
    header.setStyle(
        TableStyle(
            [
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ]
        )
    )
    story.append(header)

    if user:
        story.append(Paragraph("Customer", section_style))
        story.append(Paragraph(f"<b>{user.name}</b>", styles["Normal"]))
        story.append(Paragraph(user.email, small_style))
        if user.phone:
            story.append(Paragraph(user.phone, small_style))

    story.append(Paragraph("Items", section_style))
    item_rows = [
        [
            Paragraph("<b>Item</b>", styles["Normal"]),
            Paragraph("<b>Qty</b>", styles["Normal"]),
            Paragraph("<b>Unit Price</b>", styles["Normal"]),
            Paragraph("<b>Amount</b>", styles["Normal"]),
        ]
    ]
    for item in items:
        name = item.product.name if item.product else f"Product #{item.product_id}"
        item_rows.append(
            [
                Paragraph(name, styles["Normal"]),
                Paragraph(str(item.quantity), styles["Normal"]),
                Paragraph(_fmt_money(item.price), styles["Normal"]),
                Paragraph(_fmt_money(item.price * item.quantity), styles["Normal"]),
            ]
        )

    item_table = Table(item_rows, colWidths=[doc.width / 2.0, doc.width / 8.0,
                                             doc.width / 4.0, doc.width / 8.0])
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(item_table)

    story.append(Spacer(1, 4 * mm))
    total_rows = [
        [
            "",
            Paragraph(f"<b>Total Paid: {_fmt_money(order.total)}</b>",
                      ParagraphStyle("Total", parent=styles["Normal"], fontSize=13, alignment=TA_RIGHT)),
        ]
    ]
    total_table = Table(total_rows, colWidths=[doc.width / 2.0, doc.width / 2.0])
    total_table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (1, 0), (1, 0), 1, colors.HexColor("#1f2937")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(total_table)
    story.append(Spacer(1, 4 * mm))

    if order.mpesa_receipt:
        story.append(Paragraph("Payment", section_style))
        story.append(Paragraph(
            f"M-Pesa Receipt: <b>{order.mpesa_receipt}</b><br/>"
            f"Transaction Reference: <b>ORDER{order.id}</b>",
            styles["Normal"],
        ))

    story.append(Spacer(1, 10 * mm))
    story.append(
        Paragraph(
            "Thank you for shopping with <b>Kione Hardware</b>!",
            ParagraphStyle(
                "Thanks", parent=styles["Normal"], fontSize=11, alignment=TA_CENTER
            ),
        )
    )

    doc.build(story)
    return buf.getvalue()