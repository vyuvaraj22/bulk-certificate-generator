"""
Certificate PDF generation service using ReportLab.

Generates a single professional landscape A4 PDF certificate.
The template is predefined; data is injected per recipient.

Design decisions:
- One template keeps the code simple and testable.
- ReportLab is used because it provides fine-grained PDF control
  without requiring external binaries (unlike wkhtmltopdf).
- All dimensions are in points (1 inch = 72 pts).
"""

import logging
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

# A4 landscape dimensions
PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)


def _draw_border(c: canvas.Canvas) -> None:
    """Draw a double-line decorative border around the certificate."""
    margin_outer = 18
    margin_inner = 26

    # Outer border – gold color
    c.setStrokeColor(colors.HexColor("#C8960C"))
    c.setLineWidth(3)
    c.rect(margin_outer, margin_outer, PAGE_WIDTH - 2 * margin_outer, PAGE_HEIGHT - 2 * margin_outer)

    # Inner border – thinner
    c.setLineWidth(1)
    c.rect(margin_inner, margin_inner, PAGE_WIDTH - 2 * margin_inner, PAGE_HEIGHT - 2 * margin_inner)


def _draw_corner_ornaments(c: canvas.Canvas) -> None:
    """Draw small corner diamond ornaments."""
    c.setFillColor(colors.HexColor("#C8960C"))
    size = 7
    corners = [
        (30, 30),
        (PAGE_WIDTH - 30, 30),
        (30, PAGE_HEIGHT - 30),
        (PAGE_WIDTH - 30, PAGE_HEIGHT - 30),
    ]
    for cx, cy in corners:
        p = c.beginPath()
        p.moveTo(cx, cy + size)
        p.lineTo(cx + size, cy)
        p.lineTo(cx, cy - size)
        p.lineTo(cx - size, cy)
        p.close()
        c.drawPath(p, fill=1, stroke=0)


def _center_x(c: canvas.Canvas, text: str, font: str, size: int) -> float:
    """Calculate x coordinate to center text horizontally."""
    text_width = c.stringWidth(text, font, size)
    return (PAGE_WIDTH - text_width) / 2


def generate_certificate_pdf(
    output_path: Path,
    recipient_name: str,
    certificate_id: str,
    event_name: str,
    certificate_title: str,
    organization: str,
    issue_date: str,
    description: str | None = None,
) -> None:
    """
    Generate a single certificate PDF at the given output path.

    Args:
        output_path:       Destination file path (must not exist or will be overwritten).
        recipient_name:    Full name of the certificate recipient.
        certificate_id:    Unique certificate identifier.
        event_name:        Name of the event/course.
        certificate_title: Title to print on the certificate.
        organization:      Issuing organisation name.
        issue_date:        ISO date string (YYYY-MM-DD).
        description:       Optional subtitle / description.

    Raises:
        Exception: Any ReportLab error is propagated so callers can mark the cert as FAILED.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(output_path), pagesize=landscape(A4))
    c.setTitle(f"{certificate_title} – {recipient_name}")

    # ── Background ──────────────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#FDFAF3"))  # warm cream
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)

    # ── Decorative elements ──────────────────────────────────────────────────
    _draw_border(c)
    _draw_corner_ornaments(c)

    # Subtle horizontal rule pair
    rule_y = PAGE_HEIGHT - 80
    c.setStrokeColor(colors.HexColor("#C8960C"))
    c.setLineWidth(0.8)
    c.line(60, rule_y, PAGE_WIDTH - 60, rule_y)
    c.line(60, rule_y - 4, PAGE_WIDTH - 60, rule_y - 4)

    bottom_rule_y = 90
    c.line(60, bottom_rule_y, PAGE_WIDTH - 60, bottom_rule_y)
    c.line(60, bottom_rule_y + 4, PAGE_WIDTH - 60, bottom_rule_y + 4)

    # ── Organisation name ────────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#1A1A2E"))
    c.setFont("Helvetica-Bold", 22)
    org_text = organization.upper()
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 65, org_text)

    # ── "Certificate of Completion" title ────────────────────────────────────
    c.setFont("Helvetica", 13)
    c.setFillColor(colors.HexColor("#555577"))
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 108, "— " + certificate_title.upper() + " —")

    # ── Decorative divider ───────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#C8960C"))
    c.rect(PAGE_WIDTH / 2 - 40, PAGE_HEIGHT - 120, 80, 2, fill=1, stroke=0)

    # ── "This is to certify that" ─────────────────────────────────────────────
    c.setFont("Helvetica-Oblique", 14)
    c.setFillColor(colors.HexColor("#333344"))
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 155, "This is to certify that")

    # ── Recipient name (main hero text) ──────────────────────────────────────
    c.setFont("Helvetica-Bold", 38)
    c.setFillColor(colors.HexColor("#0D0D1A"))
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 205, recipient_name)

    # Underline beneath name
    name_width = c.stringWidth(recipient_name, "Helvetica-Bold", 38)
    name_x = (PAGE_WIDTH - name_width) / 2
    c.setStrokeColor(colors.HexColor("#C8960C"))
    c.setLineWidth(1.2)
    c.line(name_x, PAGE_HEIGHT - 213, name_x + name_width, PAGE_HEIGHT - 213)

    # ── "has successfully completed" ─────────────────────────────────────────
    c.setFont("Helvetica-Oblique", 14)
    c.setFillColor(colors.HexColor("#333344"))
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 245, "has successfully completed")

    # ── Event / course name ───────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.HexColor("#1A1A2E"))
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 280, event_name)

    # ── Optional description ──────────────────────────────────────────────────
    if description:
        c.setFont("Helvetica-Oblique", 12)
        c.setFillColor(colors.HexColor("#666688"))
        c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 308, description)

    # ── Certificate ID and date ───────────────────────────────────────────────
    # Format date nicely
    try:
        date_obj = datetime.strptime(issue_date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%d %B %Y")
    except ValueError:
        formatted_date = issue_date

    meta_y = 128
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#444466"))

    # Left: Certificate ID
    c.drawString(70, meta_y, f"Certificate ID:  {certificate_id}")

    # Right: Date
    date_str = f"Date:  {formatted_date}"
    date_width = c.stringWidth(date_str, "Helvetica", 11)
    c.drawString(PAGE_WIDTH - 70 - date_width, meta_y, date_str)

    # ── Signature area ────────────────────────────────────────────────────────
    sig_x = PAGE_WIDTH / 2
    sig_y = 112

    # Signature line
    c.setStrokeColor(colors.HexColor("#888899"))
    c.setLineWidth(0.8)
    c.line(sig_x - 80, sig_y, sig_x + 80, sig_y)

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#666688"))
    c.drawCentredString(sig_x, sig_y - 14, "Authorised Signatory")
    c.drawCentredString(sig_x, sig_y - 26, organization)

    c.save()
    logger.debug("Certificate generated: %s", output_path)
