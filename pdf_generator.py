import qrcode
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

BRAND_RED = HexColor("#B91C1C")   # red-700, consistente con El Diario
DARK = HexColor("#1F2937")
GRAY = HexColor("#6B7280")
LIGHT_BG = HexColor("#F9FAFB")


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

    # Fondo de encabezado
    c.setFillColor(BRAND_RED)
    c.rect(0, height - 35 * mm, width, 35 * mm, fill=1, stroke=0)

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
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(20 * mm, y, participant["nombre"])

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
