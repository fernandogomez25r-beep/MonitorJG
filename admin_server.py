"""
admin_server.py — Servidor de alertas del administrador
Recibe alertas del panel y las muestra como notificaciones en pantalla.
"""

import json
import threading
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

import tkinter as tk
from tkinter import messagebox

# ─── Configuración ────────────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = 5001   # Puerto separado del panel principal (5000)

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("admin_server.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ─── Alerta visual ────────────────────────────────────────────────────────────

def mostrar_alerta(data: dict):
    """Muestra un cuadro de alerta en el escritorio del administrador."""
    idle_str   = f"{data.get('idle', 0):.1f} seg"
    tiempo_str = f"{data.get('time', 0)} seg"

    mensaje = (
        f"⚠️  ACTIVIDAD NO AUTORIZADA DETECTADA\n"
        f"{'─' * 40}\n"
        f"  Empleado : {data.get('employee', 'Desconocido')}\n"
        f"  Aplicación: {data.get('app', 'N/A')}\n"
        f"  Tiempo uso: {tiempo_str}\n"
        f"  Inactividad: {idle_str}\n"
        f"{'─' * 40}"
    )

    # Tkinter debe correrse en el hilo principal → usamos after() vía hilo
    def _mostrar():
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showwarning("ALERTA — Panel de Monitoreo", mensaje)
        root.destroy()

    # Ejecutar en hilo separado para no bloquear el servidor HTTP
    threading.Thread(target=_mostrar, daemon=True).start()


# ─── Handler HTTP ─────────────────────────────────────────────────────────────

class AlertHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/":
            self._respond(200, {"status": "ok", "servidor": "admin_server", "puerto": PORT})
        else:
            self._respond(404, {"error": "Ruta no encontrada"})

    def do_POST(self):
        if self.path != "/alert":
            self._respond(404, {"error": "Ruta no encontrada"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            raw    = self.rfile.read(length)
            data   = json.loads(raw)

            log.warning(
                f"ALERTA | Empleado: {data.get('employee')} | "
                f"App: {data.get('app')} | Tiempo: {data.get('time')}s"
            )

            mostrar_alerta(data)
            self._respond(200, {"status": "alerta_mostrada"})

        except json.JSONDecodeError:
            log.error("Payload inválido recibido.")
            self._respond(400, {"error": "JSON inválido"})
        except Exception as e:
            log.error(f"Error procesando alerta: {e}")
            self._respond(500, {"error": str(e)})

    def _respond(self, code: int, body: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, format, *args):
        pass  # Silencia logs HTTP estándar (ya usamos logging propio)


# ─── Punto de entrada ─────────────────────────────────────────────────────────

def main():
    server = HTTPServer((HOST, PORT), AlertHandler)
    log.info(f"Servidor de alertas escuchando en {HOST}:{PORT}/alert")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Servidor detenido manualmente.")
        server.shutdown()


if __name__ == "__main__":
    main()
