#  Sistema de Monitoreo Empresarial

Panel de monitoreo de actividad de equipos en red local, compuesto por tres módulos independientes.

---

##  Estructura del proyecto

```
monitor/
├── panel_server.py     # Servidor web Flask — panel de administración
├── agent.py            # Agente Windows — corre en cada equipo monitoreado
├── admin_server.py     # Servidor de alertas — recibe y muestra notificaciones
├── datos.json          # Generado automáticamente — estado de los equipos
└── apps.json           # Lista de aplicaciones autorizadas
```

---

##  Configuración rápida

### 1. Instalar dependencias

```bash
pip install flask requests psutil pywin32
```

### 2. Panel web (servidor central)

Edita `panel_server.py` si necesitas cambiar el puerto (por defecto `5000`), luego:

```bash
python panel_server.py
```

Abre en tu navegador: `http://<IP-DEL-SERVIDOR>:5000`

### 3. Agente (cada PC monitoreada)

Edita estas líneas en `agent.py`:

```python
SERVER_URL = "http://192.168.1.7:5000/data"  # IP del servidor
EMPLEADO   = "PC-01"                           # Nombre único del equipo
```

Luego ejecuta (requiere Windows):

```bash
python agent.py
```

### 4. Servidor de alertas (PC del administrador)

```bash
python admin_server.py
```

Escucha en el puerto `5001`. Cuando un agente envíe una alerta, aparecerá una ventana emergente.

---

##  Flujo de datos

```
[PC Empleado]                [Servidor central]         [PC Administrador]
  agent.py  ──── /data ────▶  panel_server.py ──── /alert ──▶ admin_server.py
                                     │
                              datos.json (caché)
                                     │
                              Navegador web (panel)
```

---

##  Notas

- Los agentes reportan cada **5 segundos** de uso continuo de una app no autorizada.
- Una alerta se genera tras **60 segundos** acumulados de uso no autorizado.
- El panel web se actualiza automáticamente cada **5 segundos**.
- El archivo `apps.json` se puede editar directamente o desde el panel web.
- Todos los eventos quedan registrados en `agent.log` y `admin_server.log`.
