"""
panel_server.py — Servidor web del panel de monitoreo
Historial de usos no autorizados por equipo con sumatoria de tiempo perdido.
"""

from flask import Flask, request, jsonify, render_template_string, redirect
import json
import os
from datetime import datetime

app = Flask(__name__)

ARCHIVO_DATOS     = "datos.json"
ARCHIVO_APPS      = "apps.json"
ARCHIVO_HISTORIAL = "historial.json"

# ─── Persistencia ─────────────────────────────────────────────────────────────

def cargar_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def guardar_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

datos     = cargar_json(ARCHIVO_DATOS, {})
historial = cargar_json(ARCHIVO_HISTORIAL, {})
AUTORIZADAS = [a for a in cargar_json(ARCHIVO_APPS, ["acad.exe", "excel.exe", "winword.exe"]) if a]

# ─── HTML / UI ────────────────────────────────────────────────────────────────

HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Monitor Central</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg:       #080c14;
      --surface:  #0d1526;
      --surface2: #111d35;
      --border:   #1e304f;
      --accent:   #00d4ff;
      --accent2:  #0099bb;
      --ok:       #00e5a0;
      --warn:     #ffb830;
      --danger:   #ff4466;
      --text:     #c8ddf5;
      --muted:    #4a6080;
      --mono:     'Space Mono', monospace;
      --sans:     'Syne', sans-serif;
    }
    html { scroll-behavior: smooth; }
    body { font-family: var(--sans); background: var(--bg); color: var(--text); min-height: 100vh; overflow-x: hidden; }
    body::before {
      content: ''; position: fixed; inset: 0;
      background: radial-gradient(ellipse 60% 40% at 80% 10%, #00d4ff0d 0%, transparent 60%),
                  radial-gradient(ellipse 50% 60% at 10% 80%, #0055aa0a 0%, transparent 60%);
      pointer-events: none; z-index: 0;
    }
    body::after {
      content: ''; position: fixed; inset: 0;
      background-image: linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px);
      background-size: 40px 40px; opacity: 0.18; pointer-events: none; z-index: 0;
    }
    .layout { position: relative; z-index: 1; max-width: 1200px; margin: 0 auto; padding: 32px 24px 80px; }

    /* Header */
    header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 36px; padding-bottom: 20px; border-bottom: 1px solid var(--border); }
    .logo { display: flex; align-items: center; gap: 14px; }
    .logo-icon { width: 42px; height: 42px; border-radius: 10px; background: linear-gradient(135deg, var(--accent), #0055cc); display: flex; align-items: center; justify-content: center; font-size: 20px; box-shadow: 0 0 20px #00d4ff33; }
    .logo-text h1 { font-size: 1.3rem; font-weight: 800; color: #fff; letter-spacing: -0.5px; }
    .logo-text span { font-family: var(--mono); font-size: 0.68rem; color: var(--muted); letter-spacing: 2px; text-transform: uppercase; }
    .header-meta { text-align: right; }
    .live-badge { display: inline-flex; align-items: center; gap: 6px; font-family: var(--mono); font-size: 0.7rem; color: var(--ok); letter-spacing: 1px; text-transform: uppercase; }
    .live-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--ok); box-shadow: 0 0 8px var(--ok); animation: pulse 1.8s infinite; }
    @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.4;transform:scale(.7)} }
    .header-time { font-family: var(--mono); font-size: 0.72rem; color: var(--muted); margin-top: 4px; }

    /* Stats */
    .stats-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 28px; }
    .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; position: relative; overflow: hidden; }
    .stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; }
    .stat-card.ok-card::before     { background: var(--ok); }
    .stat-card.warn-card::before   { background: var(--warn); }
    .stat-card.danger-card::before { background: var(--danger); }
    .stat-label { font-family: var(--mono); font-size: 0.65rem; color: var(--muted); letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; }
    .stat-num   { font-size: 2rem; font-weight: 800; line-height: 1; }
    .stat-card.ok-card .stat-num     { color: var(--ok); }
    .stat-card.warn-card .stat-num   { color: var(--warn); }
    .stat-card.danger-card .stat-num { color: var(--danger); }

    /* Secciones */
    .section { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; margin-bottom: 24px; animation: fadeUp .4s ease both; }
    @keyframes fadeUp { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
    .section-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 22px; border-bottom: 1px solid var(--border); background: var(--surface2); }
    .section-title { font-size: 0.85rem; font-weight: 600; color: #fff; display: flex; align-items: center; gap: 8px; }
    .section-body { padding: 20px 22px; }

    /* Apps form */
    .app-form { display: flex; gap: 10px; margin-bottom: 18px; }
    .app-form input { flex: 1; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 9px 14px; color: var(--text); font-family: var(--mono); font-size: 0.82rem; outline: none; transition: border-color .2s; }
    .app-form input:focus { border-color: var(--accent); }
    .app-form input::placeholder { color: var(--muted); }
    .btn { padding: 9px 18px; border-radius: 8px; border: none; font-family: var(--sans); font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: all .2s; }
    .btn-primary { background: var(--accent); color: #000; }
    .btn-primary:hover { background: var(--accent2); box-shadow: 0 0 16px #00d4ff44; }
    .btn-sm { padding: 4px 10px; font-size: 0.72rem; border-radius: 6px; }
    .btn-danger { background: transparent; border: 1px solid var(--danger); color: var(--danger); }
    .btn-danger:hover { background: #ff446622; }
    .apps-list { display: flex; flex-wrap: wrap; gap: 8px; }
    .app-chip { display: flex; align-items: center; gap: 8px; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 5px 10px 5px 12px; font-family: var(--mono); font-size: 0.75rem; color: var(--text); }

    /* Tabla */
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    thead tr { border-bottom: 1px solid var(--border); }
    th { font-family: var(--mono); font-size: 0.65rem; letter-spacing: 2px; text-transform: uppercase; color: var(--muted); padding: 10px 14px; text-align: left; }
    tbody tr { border-bottom: 1px solid #1a2840; transition: background .15s; }
    tbody tr:hover { background: #0d1a2e; }
    tbody tr:last-child { border-bottom: none; }
    td { padding: 13px 14px; font-size: 0.85rem; }
    .emp-name { font-weight: 600; color: #fff; font-family: var(--mono); font-size: 0.8rem; }
    .app-name { font-family: var(--mono); font-size: 0.78rem; color: var(--accent); }
    .time-val { font-family: var(--mono); font-size: 0.8rem; }
    .ts-val   { font-family: var(--mono); font-size: 0.7rem; color: var(--muted); }
    .badge { display: inline-flex; align-items: center; gap: 5px; padding: 4px 10px; border-radius: 20px; font-family: var(--mono); font-size: 0.68rem; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; }
    .badge-ok     { background: #00e5a015; color: var(--ok);     border: 1px solid #00e5a030; }
    .badge-warn   { background: #ffb83015; color: var(--warn);   border: 1px solid #ffb83030; }
    .badge-danger { background: #ff446615; color: var(--danger); border: 1px solid #ff446630; }

    /* Historial por equipo */
    .empleados-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }
    .emp-card { background: var(--bg); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; transition: border-color .2s; }
    .emp-card:hover { border-color: #2a4060; }
    .emp-card-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; background: var(--surface2); border-bottom: 1px solid var(--border); }
    .emp-card-name { font-family: var(--mono); font-size: 0.85rem; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px; }
    .emp-card-name::before { content: ''; width: 8px; height: 8px; border-radius: 50%; background: var(--muted); flex-shrink: 0; }
    .emp-card-name.online::before { background: var(--ok); box-shadow: 0 0 6px var(--ok); }
    .total-perdido { font-family: var(--mono); font-size: 0.75rem; color: var(--danger); background: #ff446610; border: 1px solid #ff446625; border-radius: 6px; padding: 3px 8px; }
    .total-perdido.cero { color: var(--muted); background: transparent; border-color: var(--border); }
    .emp-card-body { padding: 14px 16px; }
    .uso-item { padding: 8px 0; border-bottom: 1px solid #1a2840; }
    .uso-item:last-child { border-bottom: none; }
    .uso-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
    .uso-app    { font-family: var(--mono); font-size: 0.78rem; color: var(--accent); }
    .uso-tiempo { font-family: var(--mono); font-size: 0.78rem; color: var(--danger); font-weight: 700; }
    .uso-bar-wrap { width: 100%; height: 3px; background: #1a2840; border-radius: 2px; }
    .uso-bar { height: 3px; border-radius: 2px; background: linear-gradient(90deg, var(--danger), #ff8866); transition: width .6s ease; }
    .empty-hist { text-align: center; padding: 20px; color: var(--muted); font-size: 0.8rem; font-family: var(--mono); }
    .btn-reset { background: transparent; border: 1px solid #2a3a50; color: var(--muted); font-size: 0.68rem; padding: 3px 8px; border-radius: 5px; cursor: pointer; font-family: var(--mono); transition: all .2s; }
    .btn-reset:hover { border-color: var(--danger); color: var(--danger); }

    /* Empty */
    .empty { text-align: center; padding: 48px 20px; color: var(--muted); }
    .empty-icon { font-size: 2.5rem; margin-bottom: 12px; }
    .empty p { font-size: 0.85rem; }

    @media (max-width: 600px) {
      .stats-row { grid-template-columns: 1fr; }
      header { flex-direction: column; gap: 12px; text-align: center; }
      .empleados-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<div class="layout">

  <!-- Header -->
  <header>
    <div class="logo">
      <div class="logo-icon"></div>
      <div class="logo-text">
        <h1>Monitor Central</h1>
        <span>Sistema de Monitoreo Empresarial</span>
      </div>
    </div>
    <div class="header-meta">
      <div class="live-badge"><div class="live-dot"></div>EN VIVO</div>
      <div class="header-time" id="reloj">—</div>
    </div>
  </header>

  <!-- Stats -->
  {% set total   = datos|length %}
  {% set activos = datos.values()|selectattr('app','ne','')|list|length %}
  {% set alertas = datos.values()|rejectattr('app','in',autorizadas)|list|length %}
  <div class="stats-row">
    <div class="stat-card ok-card">
      <div class="stat-label">Equipos online</div>
      <div class="stat-num" id="stat-total">{{ total }}</div>
    </div>
    <div class="stat-card warn-card">
      <div class="stat-label">Con actividad</div>
      <div class="stat-num" id="stat-activos">{{ activos }}</div>
    </div>
    <div class="stat-card danger-card">
      <div class="stat-label">No autorizados</div>
      <div class="stat-num" id="stat-alertas">{{ alertas }}</div>
    </div>
  </div>

  <!-- Apps autorizadas -->
  <div class="section">
    <div class="section-header">
      <div class="section-title"> Apps Autorizadas</div>
    </div>
    <div class="section-body">
      <form class="app-form" method="POST" action="/add_app">
        <input type="text" name="app" placeholder="ej: winword.exe" autocomplete="off" required>
        <button class="btn btn-primary" type="submit">+ Agregar</button>
      </form>
      {% if autorizadas %}
      <div class="apps-list">
        {% for a in autorizadas if a %}
        <div class="app-chip">
          {{ a }}
          <form method="POST" action="/remove_app" style="display:inline">
            <input type="hidden" name="app" value="{{ a }}">
            <button class="btn btn-danger btn-sm" type="submit">x</button>
          </form>
        </div>
        {% endfor %}
      </div>
      {% else %}
      <p style="color:var(--muted);font-size:.82rem">No hay apps registradas aún.</p>
      {% endif %}
    </div>
  </div>

  <!-- Tiempo real -->
  <div class="section">
    <div class="section-header">
      <div class="section-title"> Estado en Tiempo Real</div>
    </div>
    <div class="section-body" style="padding:0">
      {% if datos %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Equipo</th><th>App activa</th><th>Tiempo en app</th>
              <th>Inactividad</th><th>Estado</th><th>Último reporte</th>
            </tr>
          </thead>
          <tbody id="tbody-realtime">
          {% for emp, info in datos.items() %}
            <tr data-emp="{{ emp }}">
              <td><span class="emp-name">{{ emp }}</span></td>
              <td><span class="app-name">{{ info['app'] }}</span></td>
              <td><span class="time-val">{{ info['time'] }}s</span></td>
              <td><span class="time-val idle-val">{{ "%.0f"|format(info['idle']) }}s</span></td>
              <td class="td-estado">
                {% if info['idle'] > 15 %}
                  <span class="badge badge-warn">[--] Inactivo</span>
                {% elif info['app'] in autorizadas %}
                  <span class="badge badge-ok">[OK] Autorizado</span>
                {% else %}
                  <span class="badge badge-danger">[X] No autorizado</span>
                {% endif %}
              </td>
              <td><span class="ts-val">{{ info.get('timestamp','—') }}</span></td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">
        <div class="empty-icon"></div>
        <p>Sin datos aún. Los agentes reportarán en breve.</p>
      </div>
      {% endif %}
    </div>
  </div>

  <!-- Historial por equipo -->
  <div class="section">
    <div class="section-header">
      <div class="section-title"> Historial de Usos No Autorizados por Equipo</div>
    </div>
    <div class="section-body">
      {% if historial %}
      <div class="empleados-grid" id="historial-grid">
        {% for emp, usos in historial.items() %}
        {% set total_seg = usos.values()|sum %}
        {% set max_seg   = usos.values()|max if usos else 1 %}
        <div class="emp-card" data-hist-emp="{{ emp }}">
          <div class="emp-card-header">
            <div class="emp-card-name {% if emp in datos %}online{% endif %}">{{ emp }}</div>
            <div style="display:flex;align-items:center;gap:8px">
              <span class="total-perdido {% if total_seg == 0 %}cero{% endif %}">
                {{ (total_seg // 60)|int }} min perdidos
              </span>
              <form method="POST" action="/reset_historial" style="display:inline">
                <input type="hidden" name="emp" value="{{ emp }}">
                <button class="btn-reset" type="submit" title="Limpiar historial de {{ emp }}">↺</button>
              </form>
            </div>
          </div>
          <div class="emp-card-body">
            {% if usos %}
            {% for app_n, seg in usos.items()|sort(attribute='1',reverse=True) %}
            <div class="uso-item">
              <div class="uso-row">
                <span class="uso-app">{{ app_n }}</span>
                <span class="uso-tiempo">{{ (seg // 60)|int }}m {{ (seg % 60)|int }}s</span>
              </div>
              <div class="uso-bar-wrap">
                <div class="uso-bar" style="width:{{ ((seg / max_seg) * 100)|round }}%"></div>
              </div>
            </div>
            {% endfor %}
            {% else %}
            <div class="empty-hist">Sin usos no autorizados</div>
            {% endif %}
          </div>
        </div>
        {% endfor %}
      </div>
      {% else %}
      <div class="empty">
        <div class="empty-icon"></div>
        <p>Sin historial de usos no autorizados aún.</p>
      </div>
      {% endif %}
    </div>
  </div>

</div>
<script>
  const AUTORIZADAS  = {{ autorizadas | tojson }};
  const IDLE_UMBRAL  = 15; // segundos para considerar inactivo
  const estado       = {};

  // Reloj
  setInterval(() => {
    const el = document.getElementById('reloj');
    if (el) el.textContent = 'Última actualización: ' + new Date().toLocaleTimeString('es-GT');
  }, 1000);

  function fmt(s) {
    s = Math.max(0, Math.round(s));
    if (s < 60)   return s + 's';
    if (s < 3600) return Math.floor(s/60) + 'm ' + (s%60) + 's';
    return Math.floor(s/3600) + 'h ' + Math.floor((s%3600)/60) + 'm';
  }

  function badge(idle, app) {
    if (idle > IDLE_UMBRAL)        return '<span class="badge badge-warn">[--] Inactivo</span>';
    if (AUTORIZADAS.includes(app)) return '<span class="badge badge-ok">[OK] Autorizado</span>';
    return '<span class="badge badge-danger">[X] No autorizado</span>';
  }

  // Ticker cada segundo — interpola sin tocar el servidor
  setInterval(() => {
    const ahora = Date.now();
    Object.keys(estado).forEach(emp => {
      const e   = estado[emp];
      const row = document.querySelector(`tr[data-emp="${emp}"]`);
      if (!row) return;
      const elapsed  = (ahora - e.syncAt) / 1000;
      // Idle: solo crece si el usuario estaba activo (idle bajo) → se sigue acumulando
      // Si el servidor manda un idle bajo en el próximo sync, se corrige
      const idleVivo = e.idle + elapsed;
      // Tiempo en app: solo crece si estaba activo
      const timeVivo = e.idle <= IDLE_UMBRAL ? e.time + elapsed : e.time;
      const tds = row.querySelectorAll('.time-val');
      if (tds[0]) tds[0].textContent = fmt(timeVivo);
      if (tds[1]) tds[1].textContent = fmt(idleVivo);
      row.querySelector('.td-estado').innerHTML = badge(idleVivo, e.app);
    });
  }, 1000);

  // Sync cada 5s
  async function sync() {
    try {
      const [resDatos, resHist] = await Promise.all([
        fetch('/api/datos'),
        fetch('/api/historial'),
      ]);
      const data = await resDatos.json();
      const hist = await resHist.json();
      const keys = Object.keys(data);

      // Stats
      document.getElementById('stat-total').textContent   = keys.length;
      document.getElementById('stat-activos').textContent = keys.filter(k => data[k].app).length;
      document.getElementById('stat-alertas').textContent = keys.filter(k => !AUTORIZADAS.includes(data[k].app) && data[k].idle <= IDLE_UMBRAL).length;

      // Tiempo real
      const tbody = document.getElementById('tbody-realtime');
      if (tbody) {
        keys.forEach(emp => {
          const info = data[emp];
          // Al recibir sync: el idle real del servidor REEMPLAZA la estimación local
          // Si el usuario movió el mouse, idle vendrá bajo → se corrige aquí
          estado[emp] = {
            app:    info.app,
            time:   Number(info.time),
            idle:   Number(info.idle),
            syncAt: Date.now(),
          };
          let row = tbody.querySelector(`tr[data-emp="${emp}"]`);
          if (!row) {
            row = document.createElement('tr');
            row.setAttribute('data-emp', emp);
            row.innerHTML = `
              <td><span class="emp-name">${emp}</span></td>
              <td><span class="app-name"></span></td>
              <td><span class="time-val"></span></td>
              <td><span class="time-val idle-val"></span></td>
              <td class="td-estado"></td>
              <td><span class="ts-val"></span></td>`;
            tbody.appendChild(row);
          }
          row.querySelector('.app-name').textContent = info.app || '—';
          row.querySelector('.ts-val').textContent   = info.timestamp || '—';
        });
        tbody.querySelectorAll('tr[data-emp]').forEach(row => {
          const emp = row.getAttribute('data-emp');
          if (!data[emp]) { delete estado[emp]; row.remove(); }
        });
      }

      // Historial
      const grid = document.getElementById('historial-grid');
      if (!grid) return;

      const empOnline = new Set(keys);
      Object.keys(hist).forEach(emp => {
        const usos    = hist[emp];
        const entries = Object.entries(usos).sort((a,b) => b[1]-a[1]);
        const totalSeg = entries.reduce((s,[,v]) => s+v, 0);
        const maxSeg   = entries.length ? entries[0][1] : 1;

        let card = grid.querySelector(`[data-hist-emp="${emp}"]`);
        if (!card) {
          card = document.createElement('div');
          card.className = 'emp-card';
          card.setAttribute('data-hist-emp', emp);
          card.innerHTML = `
            <div class="emp-card-header">
              <div class="emp-card-name"></div>
              <div style="display:flex;align-items:center;gap:8px">
                <span class="total-perdido"></span>
                <form method="POST" action="/reset_historial" style="display:inline">
                  <input type="hidden" name="emp" value="${emp}">
                  <button class="btn-reset" type="submit">↺</button>
                </form>
              </div>
            </div>
            <div class="emp-card-body"></div>`;
          grid.appendChild(card);
        }

        // Nombre + online dot
        const nameEl = card.querySelector('.emp-card-name');
        nameEl.textContent = emp;
        nameEl.className   = 'emp-card-name' + (empOnline.has(emp) ? ' online' : '');

        // Total perdido
        const totalEl = card.querySelector('.total-perdido');
        const mins    = Math.floor(totalSeg / 60);
        totalEl.textContent = mins + ' min perdidos';
        totalEl.className   = 'total-perdido' + (totalSeg === 0 ? ' cero' : '');

        // Lista de usos
        const body = card.querySelector('.emp-card-body');
        if (entries.length === 0) {
          body.innerHTML = '<div class="empty-hist">Sin usos no autorizados</div>';
        } else {
          body.innerHTML = entries.map(([appN, seg]) => `
            <div class="uso-item">
              <div class="uso-row">
                <span class="uso-app">${appN}</span>
                <span class="uso-tiempo">${Math.floor(seg/60)}m ${Math.round(seg%60)}s</span>
              </div>
              <div class="uso-bar-wrap">
                <div class="uso-bar" style="width:${Math.round(seg/maxSeg*100)}%"></div>
              </div>
            </div>`).join('');
        }
      });

    } catch(e) { console.warn('Sin conexión:', e); }
  }

  // Inicializar estado desde HTML inicial
  document.querySelectorAll('#tbody-realtime tr[data-emp]').forEach(row => {
    const emp  = row.querySelector('.emp-name')?.textContent.trim();
    const tds  = row.querySelectorAll('.time-val');
    if (emp) estado[emp] = {
      app:    row.querySelector('.app-name')?.textContent.trim() || '',
      time:   parseFloat(tds[0]?.textContent) || 0,
      idle:   parseFloat(tds[1]?.textContent) || 0,
      syncAt: Date.now(),
    };
  });

  sync();
  setInterval(sync, 5000);
</script>
</body>
</html>
"""

# ─── Rutas ────────────────────────────────────────────────────────────────────

@app.route("/")
def panel():
    return render_template_string(HTML, datos=datos, autorizadas=AUTORIZADAS, historial=historial)


@app.route("/add_app", methods=["POST"])
def add_app():
    nombre = request.form.get("app", "").strip().lower()
    if nombre and nombre not in AUTORIZADAS:
        AUTORIZADAS.append(nombre)
        guardar_json(ARCHIVO_APPS, AUTORIZADAS)
    return redirect("/")


@app.route("/remove_app", methods=["POST"])
def remove_app():
    nombre = request.form.get("app", "").strip()
    if nombre in AUTORIZADAS:
        AUTORIZADAS.remove(nombre)
        guardar_json(ARCHIVO_APPS, AUTORIZADAS)
    return redirect("/")


@app.route("/reset_historial", methods=["POST"])
def reset_historial():
    emp = request.form.get("emp", "").strip()
    if emp in historial:
        historial[emp] = {}
        guardar_json(ARCHIVO_HISTORIAL, historial)
    return redirect("/")


@app.route("/data", methods=["POST"])
def recibir():
    data = request.json
    if not data or "employee" not in data:
        return jsonify({"error": "Payload inválido"}), 400

    emp      = data["employee"]
    app_name = data.get("app", "")
    idle     = float(data.get("idle", 0))
    tiempo   = int(data.get("time", 0))

    data["timestamp"] = datetime.now().strftime("%H:%M:%S")
    datos[emp] = data
    guardar_json(ARCHIVO_DATOS, datos)

    # Acumular en historial solo si:
    # - la app NO está autorizada
    # - el usuario estaba activo (idle <= 15s)
    # - hay tiempo acumulado real
    if app_name and app_name not in AUTORIZADAS and idle <= 15 and tiempo > 0:
        if emp not in historial:
            historial[emp] = {}
        historial[emp][app_name] = historial[emp].get(app_name, 0) + tiempo
        guardar_json(ARCHIVO_HISTORIAL, historial)

    return jsonify({"status": "ok"})


@app.route("/api/datos")
def api_datos():
    return jsonify(datos)


@app.route("/api/historial")
def api_historial():
    return jsonify(historial)


# ─── Inicio ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
