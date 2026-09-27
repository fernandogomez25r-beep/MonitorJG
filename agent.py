"""
agent.py — Agente de monitoreo de actividad (Windows)
Envía datos de uso de aplicaciones al servidor central cada ciclo.
Notificación nativa de Windows cada 7 minutos de uso no autorizado acumulado.
"""

import time
import ctypes
import logging
import requests
import win32gui
import win32process
import psutil
from winotify import Notification, audio

# ─── Configuración ────────────────────────────────────────────────────────────
SERVER_URL      = "http://192.168.1.7:5000/data"   # ⚠️ Cambia por la IP del servidor
EMPLEADO        = "PC-01"                           # ⚠️ Nombre único de este equipo
INTERVALO       = 5        # segundos entre cada revisión
UMBRAL_NOTIF    = 420      # 7 minutos acumulados → notificación Windows
UMBRAL_IDLE     = 15       # segundos sin actividad para considerar "inactivo"

NO_AUTORIZADAS_LOCAL = ["chrome.exe", "msedge.exe", "firefox.exe", "steam.exe"]

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("agent.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ─── Funciones ────────────────────────────────────────────────────────────────

def get_idle_time() -> float:
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(lii)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
    return millis / 1000.0


def get_active_app() -> str:
    hwnd = win32gui.GetForegroundWindow()
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    return psutil.Process(pid).name().lower()


def enviar_datos(payload: dict) -> bool:
    try:
        resp = requests.post(SERVER_URL, json=payload, timeout=5)
        resp.raise_for_status()
        log.info(f"Datos enviados → {payload['app']} | {payload['time']}s")
        return True
    except requests.exceptions.ConnectionError:
        log.warning("Sin conexión al servidor.")
    except requests.exceptions.Timeout:
        log.warning("Tiempo de espera agotado.")
    except Exception as e:
        log.error(f"Error al enviar datos: {e}")
    return False


def notificar_windows(app: str, minutos: int):
    """Muestra una notificación discreta en el panel de notificaciones de Windows."""
    try:
        toast = Notification(
            app_id="Monitor Empresarial",
            title="⚠️ Uso no autorizado detectado",
            msg=f"{EMPLEADO} lleva {minutos} min usando {app}",
            duration="short",   # desaparece sola, no interrumpe
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
        log.warning(f"Notificación enviada → {app} | {minutos} min")
    except Exception as e:
        log.error(f"Error al mostrar notificación: {e}")


# ─── Bucle principal ──────────────────────────────────────────────────────────

def main():
    log.info(f"Agente iniciado → Empleado: {EMPLEADO} | Servidor: {SERVER_URL}")

    # Tiempo acumulado total por app no autorizada (para notificación cada 7 min)
    acum_total    = {}   # { "chrome.exe": 420, ... }
    ultimo_notif  = {}   # { "chrome.exe": 420, ... } — último acumulado al notificar
    app_anterior  = None
    tiempo_sesion = 0    # segundos en la sesión actual de la app activa

    while True:
        try:
            app  = get_active_app()
            idle = get_idle_time()
            activo = idle <= UMBRAL_IDLE

            # Si cambió de app o el usuario está inactivo → reiniciar sesión
            if app != app_anterior or not activo:
                tiempo_sesion = 0
                app_anterior  = app

            if app in NO_AUTORIZADAS_LOCAL and activo:
                tiempo_sesion += INTERVALO
                acum_total[app] = acum_total.get(app, 0) + INTERVALO

                # Notificación cada 7 minutos acumulados por app
                notif_prev = ultimo_notif.get(app, 0)
                if acum_total[app] >= UMBRAL_NOTIF and acum_total[app] // 60 > notif_prev // 60:
                    notificar_windows(app, int(acum_total[app] // 60))
                    ultimo_notif[app] = acum_total[app]
            else:
                tiempo_sesion = 0

            # Siempre reportar estado actual al servidor
            payload = {
                "employee": EMPLEADO,
                "app":      app,
                "time":     tiempo_sesion,   # tiempo en la sesión actual
                "idle":     round(idle, 2),
            }
            enviar_datos(payload)

        except Exception as e:
            log.error(f"Error en el ciclo principal: {e}")

        time.sleep(INTERVALO)

        time.sleep(INTERVALO)


if __name__ == "__main__":
    main()
