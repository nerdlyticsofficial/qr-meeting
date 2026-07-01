import os
import csv
import io
from flask import (
    Flask, render_template, request, redirect, url_for,
    send_file, flash, abort, Response
)
from database import init_db, get_db
from pdf_generator import generate_participant_pdf, generate_meeting_qr

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QR_DIR = os.path.join(BASE_DIR, "static", "qr")
PDF_DIR = os.path.join(BASE_DIR, "static", "pdfs")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-cambiar-en-produccion")

os.makedirs(QR_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

init_db()


def base_url():
    # Respeta el host real (útil detrás de proxies en hosting)
    return request.url_root.rstrip("/")


# ---------- ADMIN ----------

@app.route("/")
def index():
    return redirect(url_for("admin_dashboard"))


@app.route("/admin")
def admin_dashboard():
    with get_db() as conn:
        meetings = conn.execute("""
            SELECT m.*, COUNT(p.id) as total_participantes
            FROM meetings m
            LEFT JOIN participants p ON p.meeting_id = m.id
            GROUP BY m.id
            ORDER BY m.id DESC
        """).fetchall()
    return render_template("admin_dashboard.html", meetings=meetings)


@app.route("/admin/meetings/new", methods=["GET", "POST"])
def new_meeting():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        fecha = request.form.get("fecha", "").strip()
        lugar = request.form.get("lugar", "").strip()
        organizador = request.form.get("organizador", "").strip()

        if not nombre:
            flash("El nombre de la reunión es obligatorio.", "error")
            return render_template("meeting_form.html")

        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO meetings (nombre, fecha, lugar, organizador) VALUES (?,?,?,?)",
                (nombre, fecha, lugar, organizador),
            )
            meeting_id = cur.lastrowid

        # Generar QR que apunta al formulario público de esta reunión
        registro_url = f"{base_url()}/r/{meeting_id}"
        qr_path = os.path.join(QR_DIR, f"meeting_{meeting_id}.png")
        generate_meeting_qr(qr_path, registro_url)

        flash("Reunión creada. Comparte el QR para el registro.", "success")
        return redirect(url_for("meeting_detail", meeting_id=meeting_id))

    return render_template("meeting_form.html")


@app.route("/admin/meetings/<int:meeting_id>")
def meeting_detail(meeting_id):
    with get_db() as conn:
        meeting = conn.execute("SELECT * FROM meetings WHERE id=?", (meeting_id,)).fetchone()
        if not meeting:
            abort(404)
        participants = conn.execute(
            "SELECT * FROM participants WHERE meeting_id=? ORDER BY id DESC", (meeting_id,)
        ).fetchall()

    qr_filename = f"meeting_{meeting_id}.png"
    qr_full_path = os.path.join(QR_DIR, qr_filename)
    if not os.path.exists(qr_full_path):
        generate_meeting_qr(qr_full_path, f"{base_url()}/r/{meeting_id}")

    return render_template(
        "meeting_detail.html",
        meeting=meeting,
        participants=participants,
        qr_filename=qr_filename,
        registro_url=f"{base_url()}/r/{meeting_id}",
    )


@app.route("/admin/meetings/<int:meeting_id>/participants.json")
def participants_json(meeting_id):
    with get_db() as conn:
        meeting = conn.execute("SELECT id FROM meetings WHERE id=?", (meeting_id,)).fetchone()
        if not meeting:
            abort(404)
        participants = conn.execute(
            "SELECT * FROM participants WHERE meeting_id=? ORDER BY id DESC", (meeting_id,)
        ).fetchall()

    return {
        "total": len(participants),
        "participants": [
            {
                "id": p["id"],
                "nombre": p["nombre"],
                "empresa": p["empresa"],
                "email": p["email"],
                "registered_at": p["registered_at"],
                "pdf_path": p["pdf_path"],
            }
            for p in participants
        ],
    }


@app.route("/admin/meetings/<int:meeting_id>/delete", methods=["POST"])
def delete_meeting(meeting_id):
    with get_db() as conn:
        conn.execute("DELETE FROM meetings WHERE id=?", (meeting_id,))
    qr_path = os.path.join(QR_DIR, f"meeting_{meeting_id}.png")
    if os.path.exists(qr_path):
        os.remove(qr_path)
    flash("Reunión eliminada.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/meetings/<int:meeting_id>/export.csv")
def export_csv(meeting_id):
    with get_db() as conn:
        meeting = conn.execute("SELECT * FROM meetings WHERE id=?", (meeting_id,)).fetchone()
        if not meeting:
            abort(404)
        participants = conn.execute(
            "SELECT * FROM participants WHERE meeting_id=? ORDER BY id", (meeting_id,)
        ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Nombre", "Documento", "Email", "Teléfono", "Empresa", "Cargo", "Registrado"])
    for p in participants:
        writer.writerow([p["id"], p["nombre"], p["documento"], p["email"],
                          p["telefono"], p["empresa"], p["cargo"], p["registered_at"]])

    filename = f"participantes_{meeting['nombre'].replace(' ', '_')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------- FORMULARIO PÚBLICO (escaneado por QR) ----------

@app.route("/r/<int:meeting_id>", methods=["GET", "POST"])
def register_participant(meeting_id):
    with get_db() as conn:
        meeting = conn.execute("SELECT * FROM meetings WHERE id=?", (meeting_id,)).fetchone()

    if not meeting:
        return render_template("not_found.html"), 404

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        documento = request.form.get("documento", "").strip()
        email = request.form.get("email", "").strip()
        telefono = request.form.get("telefono", "").strip()
        empresa = request.form.get("empresa", "").strip()
        cargo = request.form.get("cargo", "").strip()

        if not nombre:
            flash("El nombre es obligatorio.", "error")
            return render_template("register_form.html", meeting=meeting, form=request.form)

        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO participants
                   (meeting_id, nombre, documento, email, telefono, empresa, cargo)
                   VALUES (?,?,?,?,?,?,?)""",
                (meeting_id, nombre, documento, email, telefono, empresa, cargo),
            )
            participant_id = cur.lastrowid
            participant = conn.execute(
                "SELECT * FROM participants WHERE id=?", (participant_id,)
            ).fetchone()

        # Generar PDF individual
        pdf_filename = f"participante_{participant_id}.pdf"
        pdf_path = os.path.join(PDF_DIR, pdf_filename)
        verify_url = f"{base_url()}/pdf/{participant_id}"
        generate_participant_pdf(pdf_path, dict(meeting), dict(participant), verify_url)

        with get_db() as conn:
            conn.execute(
                "UPDATE participants SET pdf_path=? WHERE id=?",
                (pdf_filename, participant_id),
            )

        return redirect(url_for("registration_success", participant_id=participant_id))

    return render_template("register_form.html", meeting=meeting, form={})


@app.route("/success/<int:participant_id>")
def registration_success(participant_id):
    with get_db() as conn:
        participant = conn.execute(
            "SELECT p.*, m.nombre as meeting_nombre FROM participants p "
            "JOIN meetings m ON m.id = p.meeting_id WHERE p.id=?",
            (participant_id,),
        ).fetchone()
    if not participant:
        abort(404)
    return render_template("success.html", participant=participant)


@app.route("/pdf/<int:participant_id>")
def download_pdf(participant_id):
    with get_db() as conn:
        participant = conn.execute(
            "SELECT * FROM participants WHERE id=?", (participant_id,)
        ).fetchone()
    if not participant or not participant["pdf_path"]:
        abort(404)
    path = os.path.join(PDF_DIR, participant["pdf_path"])
    if not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=False, download_name=participant["pdf_path"])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
