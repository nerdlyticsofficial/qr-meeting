# Sistema de Registro por QR para Reuniones (MVP)

App web simple para gestionar el registro de participantes en reuniones mediante código QR.

## Flujo

1. Desde el **panel admin** (`/admin`) creas una reunión → se genera un **QR** automáticamente.
2. Imprimes o proyectas ese QR en la entrada de la reunión.
3. Cada participante lo **escanea con su celular**, se abre un formulario, llena sus datos y confirma.
4. Sus datos quedan guardados en la base de datos y se genera automáticamente un **PDF de constancia/credencial** que puede descargar al instante.
5. Desde el panel admin puedes ver la lista de participantes en tiempo real, descargar sus PDFs individuales o **exportar todo a CSV**.

## Instalación local

```bash
cd qr-meeting-app
python3 -m venv venv
source venv/bin/activate          # En Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abre `http://127.0.0.1:5000/admin` en tu navegador.

> **Importante sobre el QR y el celular:** el QR apunta a la URL desde la que corre el servidor (`request.url_root`). Si corres esto en tu laptop y quieres que otros celulares en la misma red escaneen el QR, necesitas que el servidor sea accesible desde la red (ver abajo) o publicarlo en internet (recomendado para uso real en reuniones).

### Probar en la misma red Wi-Fi (sin desplegar)

```bash
python app.py
```

Y accede desde el celular a `http://TU_IP_LOCAL:5000/admin` — el QR generado usará automáticamente esa IP si accedes al panel admin desde esa misma IP.

## Estructura del proyecto

```
qr-meeting-app/
├── app.py                  # Rutas Flask (admin, formulario público, PDFs)
├── database.py              # SQLite: esquema y conexión
├── pdf_generator.py         # Generación de QR y PDF de constancia (reportlab)
├── requirements.txt
├── data/app.db               # Base de datos SQLite (se crea sola al arrancar)
├── static/
│   ├── css/style.css
│   ├── qr/                  # QRs generados por reunión
│   └── pdfs/                # PDFs generados por participante
└── templates/                # HTML (Jinja2)
```

## Desplegar "en línea" para uso real en reuniones

Para que el QR funcione al escanearlo desde cualquier celular (no solo tu red local), necesitas subirlo a un hosting. Opciones simples y gratuitas/económicas para un MVP:

- **Render.com** (recomendado, gratis para empezar): sube el repo a GitHub, crea un "Web Service", build command `pip install -r requirements.txt`, start command `gunicorn app:app`.
- **PythonAnywhere**: soporta Flask nativamente, plan gratuito disponible.
- **Railway.app**: similar a Render, despliegue por Git.

Antes de desplegar en producción, agrega a `requirements.txt`:
```
gunicorn
```
Y usa como start command:
```
gunicorn app:app
```

### Variables de entorno recomendadas en producción
- `SECRET_KEY`: una cadena aleatoria segura (Flask la usa para las sesiones/flash messages).

## Campos del formulario (por defecto)

Nombre completo (obligatorio), documento/cédula, email, teléfono, empresa/institución, cargo.
Puedes editar estos campos en `templates/register_form.html` y las columnas correspondientes en `database.py` / `app.py`.

## Notas del MVP (siguientes pasos sugeridos)

- No tiene autenticación en `/admin` — cualquiera con la URL puede administrar. Para uso real, agregar login (Flask-Login) antes de desplegar públicamente.
- La base de datos es SQLite (archivo único) — suficiente para el volumen de una reunión/evento; si esperas cientos de eventos concurrentes, migrar a PostgreSQL es sencillo cambiando `database.py`.
- El PDF incluye un QR de verificación individual (apunta a `/pdf/<id>`) por si luego quieres usarlo para control de acceso/check-in.
