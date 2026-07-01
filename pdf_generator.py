import qrcode
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

import os

BRAND_NAVY = HexColor("#023877")   # azul institucional ITLA
BRAND_RED = HexColor("#E52229")    # rojo de acento ITLA
DARK = HexColor("#1F2937")
GRAY = HexColor("#6B7280")
LIGHT_BG = HexColor("#F9FAFB")

LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "img", "itla-logo.png")
LOGO_WHITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "img", "itla-logo-white.png")


def _qr_image(data: str):
    qr = qrcode.QRCode(border=1, box_size=8)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def generate_participant_pdf(path: str, meeting: dict, participant: dict, verify_url: str):
    """Genera una constancia/credencial de participante en formato media carta."""
    width, height = letter
    c = canvas.Canvas(path, pagesize=letter)

    # Fondo de encabezado (azul institucional) con barra roja de acento
    c.setFillColor(BRAND_NAVY)
    c.rect(0, height - 35 * mm, width, 35 * mm, fill=1, stroke=0)
    c.setFillColor(BRAND_RED)
    c.rect(0, height - 36.5 * mm, width, 1.5 * mm, fill=1, stroke=0)

    # Logo ITLA en blanco (esquina superior derecha del encabezado azul)
    if os.path.exists(LOGO_WHITE_PATH):
        logo = ImageReader(LOGO_WHITE_PATH)
        logo_h = 16 * mm
        logo_w = logo_h * (347 / 200)  # proporción real del logo
        c.drawImage(
            logo, width - 20 * mm - logo_w, height - 26 * mm, logo_w, logo_h,
            mask="auto",
        )

    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 20)
    c.drawString(20 * mm, height - 20 * mm, meeting["nombre"] or "Reunión")

    c.setFont("Helvetica", 11)
    fecha_lugar = " | ".join([v for v in [meeting.get("fecha"), meeting.get("lugar")] if v])
    if fecha_lugar:
        c.drawString(20 * mm, height - 28 * mm, fecha_lugar)

    # Etiqueta
    y = height - 50 * mm
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, "CONSTANCIA DE PARTICIPACIÓN")

    # Nombre del participante
    y -= 12 * mm
    c.setFillColor(BRAND_NAVY)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(20 * mm, y, participant["nombre"])

    # Barra roja de acento (detalle de marca ITLA)
    c.setFillColor(BRAND_RED)
    c.rect(20 * mm, y - 4 * mm, 22 * mm, 1.2 * mm, fill=1, stroke=0)

    # Datos adicionales
    y -= 10 * mm
    c.setFont("Helvetica", 11)
    c.setFillColor(GRAY)
    campos = [
        ("Empresa / Institución", participant.get("empresa")),
        ("Cargo", participant.get("cargo")),
        ("Email", participant.get("email")),
        ("Teléfono", participant.get("telefono")),
        ("Documento", participant.get("documento")),
    ]
    for label, value in campos:
        if value:
            c.setFillColor(GRAY)
            c.setFont("Helvetica", 9)
            c.drawString(20 * mm, y, label.upper())
            c.setFillColor(DARK)
            c.setFont("Helvetica", 12)
            c.drawString(20 * mm, y - 5 * mm, str(value))
            y -= 15 * mm

    # QR de verificación (esquina inferior derecha)
    qr_img = _qr_image(verify_url)
    qr_size = 35 * mm
    c.drawImage(qr_img, width - 20 * mm - qr_size, 20 * mm, qr_size, qr_size)
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY)
    c.drawCentredString(width - 20 * mm - qr_size / 2, 16 * mm, "Código de verificación")

    # Pie
    c.setStrokeColor(HexColor("#E5E7EB"))
    c.line(20 * mm, 14 * mm, width - 20 * mm, 14 * mm)
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY)
    c.drawString(20 * mm, 10 * mm, f"Registrado: {participant.get('registered_at', '')}")
    c.drawRightString(width - 20 * mm, 10 * mm, f"ID Participante: {participant['id']}")

    c.showPage()
    c.save()


def generate_meeting_qr(path: str, url: str):
    qr = qrcode.QRCode(border=2, box_size=10)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(path)
