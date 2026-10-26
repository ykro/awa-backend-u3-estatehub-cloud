"""Consola web de EstateHub Cloud.

Reglas de seguridad de esta página (ver la CSP en app/main.py):
- Todo dato del servidor o del usuario se pinta con textContent; nunca con innerHTML.
- Sin scripts ni estilos externos: CSS y JS en línea con el nonce de cada respuesta.
- Sin manejadores onclick en el HTML (la CSP los bloquea): se usa addEventListener.
- El formulario de login arranca vacío y la consola nunca muestra contraseñas.
- El token vive solo en memoria de la pestaña (no en localStorage).
"""

from __future__ import annotations

_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EstateHub Cloud - Consola de seguridad</title>
<style nonce="__NONCE__">
:root {
  --page: #F8FAFC; --surface: #FFFFFF; --muted: #F1F5F9; --line: #E2E8F0;
  --ink: #0F172A; --body: #334155; --soft: #64748B;
  --green: #047857; --green-bg: #ECFDF5; --green-line: #A7F3D0;
  --blue: #1D4ED8; --blue-bg: #EFF6FF; --blue-line: #BFDBFE;
  --amber: #B45309; --amber-bg: #FFFBEB; --amber-line: #FDE68A;
  --red: #BE123C; --red-bg: #FFF1F2; --red-line: #FECDD3;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
code, pre, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
header { background: var(--surface); border-bottom: 1px solid var(--line); }
.bar { max-width: 1180px; margin: 0 auto; padding: 16px 24px; display: flex; flex-wrap: wrap;
  gap: 16px; align-items: center; justify-content: space-between; }
.brand { display: flex; gap: 12px; align-items: center; }
.logo { width: 40px; height: 40px; border-radius: 10px; background: var(--green); color: #FFFFFF;
  font-weight: 800; display: flex; align-items: center; justify-content: center; font-size: 18px; }
h1 { font-size: 18px; margin: 0; }
.sub { font-size: 12.5px; color: var(--soft); margin: 2px 0 0; }
.session { font-size: 12.5px; padding: 7px 12px; border-radius: 8px; border: 1px solid var(--line);
  background: var(--muted); color: var(--body); }
.session.on { background: var(--green-bg); border-color: var(--green-line); color: var(--green); font-weight: 700; }
nav { max-width: 1180px; margin: 0 auto; padding: 0 24px; display: flex; gap: 4px; flex-wrap: wrap; }
.tab { border: 0; background: none; padding: 12px 14px; font-size: 14px; font-weight: 600;
  color: var(--soft); border-bottom: 2px solid transparent; cursor: pointer; font-family: inherit; }
.tab.active { color: var(--green); border-bottom-color: var(--green); }
main { max-width: 1180px; margin: 24px auto 48px; padding: 0 24px; }
.panel { display: none; }
.panel.active { display: grid; grid-template-columns: 5fr 7fr; gap: 20px; }
@media (max-width: 900px) { .panel.active { grid-template-columns: 1fr; } }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 20px; margin-bottom: 20px; }
.card h2 { font-size: 16px; margin: 0 0 6px; }
.card p { font-size: 13.5px; color: var(--body); line-height: 1.55; margin: 6px 0 12px; }
label { display: block; font-size: 12.5px; font-weight: 600; color: var(--body); margin: 10px 0 4px; }
input, select { width: 100%; padding: 9px 10px; font-size: 14px; border: 1px solid #CBD5E1;
  border-radius: 8px; background: #FFFFFF; color: var(--ink); font-family: inherit; }
.row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.btn { border: 1px solid var(--line); background: var(--surface); color: var(--ink); padding: 9px 14px;
  border-radius: 8px; font-size: 13.5px; font-weight: 600; cursor: pointer; font-family: inherit; }
a.btn { text-decoration: none; display: inline-block; }
.btn.primary { background: var(--green); border-color: var(--green); color: #FFFFFF; }
.btn.danger { background: var(--red-bg); border-color: var(--red-line); color: var(--red); }
pre { background: #F6F8FA; border: 1px solid var(--line); border-radius: 10px; padding: 12px;
  font-size: 12.5px; color: var(--ink); overflow-x: auto; white-space: pre-wrap; word-break: break-word; min-height: 64px; margin: 8px 0 0; }
.note { font-size: 12.5px; padding: 10px 12px; border-radius: 8px; border: 1px solid var(--line);
  background: var(--muted); color: var(--body); margin-top: 12px; }
.note.ok { background: var(--green-bg); border-color: var(--green-line); color: var(--green); }
.note.warn { background: var(--amber-bg); border-color: var(--amber-line); color: var(--amber); }
.note.bad { background: var(--red-bg); border-color: var(--red-line); color: var(--red); }
.grid { margin-top: 14px; display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
.prop { border: 1px solid var(--line); border-radius: 10px; padding: 14px; background: #FCFCFD; }
.prop .meta { font-size: 11.5px; color: var(--green); font-weight: 700; }
.prop h3 { font-size: 14.5px; margin: 6px 0 4px; overflow-wrap: anywhere; }
.prop .line { font-size: 12.5px; color: var(--body); margin: 2px 0; }
.prop .pitch { overflow-wrap: anywhere; font-size: 12.5px; color: var(--body); background: var(--muted); border-radius: 8px; padding: 8px; margin-top: 8px; }
.empty { font-size: 13px; color: var(--soft); }
.card h2.spaced { margin-top: 22px; }
</style>
</head>
<body>
<header>
  <div class="bar">
    <div class="brand">
      <div class="logo">E</div>
      <div>
        <h1>EstateHub Cloud API</h1>
        <p class="sub">Curso 1, Unidad 3. Autenticación JWT, autorización por propietario y Cloud Run.</p>
      </div>
    </div>
    <div class="row">
      <span id="session-badge" class="session">Sin sesión</span>
      <a class="btn" href="/docs">Swagger /docs</a>
    </div>
  </div>
  <nav>
    <button class="tab active" data-tab="catalog" type="button">1. Sesión y catálogo</button>
    <button class="tab" data-tab="authz" type="button">2. Autorización 401 y 403</button>
    <button class="tab" data-tab="pitch" type="button">3. Pitch y explorador HTTP</button>
  </nav>
</header>

<main>
  <section id="panel-catalog" class="panel active">
    <div>
      <div class="card">
        <h2>Iniciar sesión</h2>
        <p>Escribe las credenciales de un agente. En local, las de demostración están en tu archivo <code>.env</code>; en la nube no existen usuarios de demostración.</p>
        <form id="login-form" autocomplete="off">
          <label for="login-email">Correo</label>
          <input id="login-email" type="email" autocomplete="username" required>
          <label for="login-password">Contraseña</label>
          <input id="login-password" type="password" autocomplete="current-password" required>
          <div class="row">
            <button class="btn primary" type="submit">Obtener token</button>
            <button class="btn" id="logout-btn" type="button">Cerrar sesión</button>
          </div>
        </form>
        <div id="login-note" class="note">Sin token: las rutas protegidas responden 401.</div>
      </div>
      <div class="card">
        <h2>Claims del token</h2>
        <p>El payload de un JWT es legible por cualquiera (Base64Url). Lo que lo protege es la firma.</p>
        <pre id="claims-box">Sin token activo.</pre>
      </div>
    </div>
    <div>
      <div class="card">
        <h2>Catálogo público</h2>
        <p>El DTO público muestra el nombre del agente dueño, no su correo.</p>
        <div class="row"><button class="btn" id="reload-btn" type="button">Recargar catálogo</button></div>
        <div id="property-grid" class="grid"></div>
      </div>
      <div class="card">
        <h2>Publicar inmueble (requiere token)</h2>
        <p>El dueño se toma del token; el body no puede traer <code>owner_agent_id</code>.</p>
        <form id="create-form">
          <label for="new-title">Título</label>
          <input id="new-title" type="text" maxlength="120" required>
          <label for="new-city">Ciudad</label>
          <input id="new-city" type="text" maxlength="60" required>
          <label for="new-price">Precio en USD</label>
          <input id="new-price" type="number" min="1" max="50000000" required>
          <label for="new-bedrooms">Habitaciones</label>
          <input id="new-bedrooms" type="number" min="1" max="20" value="2" required>
          <div class="row"><button class="btn primary" type="submit">Crear inmueble</button></div>
        </form>
        <div id="create-note" class="note">Sin enviar.</div>
      </div>
    </div>
  </section>

  <section id="panel-authz" class="panel">
    <div class="card">
      <h2>Prueba de autorización por propietario</h2>
      <p>Inicia sesión como un agente e intenta cambiar o borrar un inmueble de otro agente. La API debe responder 403 aunque el token sea válido.</p>
      <label for="authz-property">Inmueble</label>
      <select id="authz-property"></select>
      <label for="authz-status">Nuevo estado</label>
      <select id="authz-status">
        <option value="reserved">Reservado</option>
        <option value="sold">Vendido</option>
        <option value="available">Disponible</option>
      </select>
      <div class="row">
        <button class="btn primary" id="patch-btn" type="button">PATCH /status</button>
        <button class="btn danger" id="delete-btn" type="button">DELETE inmueble</button>
      </div>
      <div id="authz-note" class="note">Esperando prueba.</div>
    </div>
    <div class="card">
      <h2>Respuesta de la API</h2>
      <pre id="authz-output">{}</pre>
    </div>
  </section>

  <section id="panel-pitch" class="panel">
    <div class="card">
      <h2>Pitch comercial</h2>
      <p>Solo el dueño del inmueble o un admin pueden generarlo. Sin llave de Gemini se usa un pitch determinista con el mismo contrato.</p>
      <label for="pitch-property">Inmueble</label>
      <select id="pitch-property"></select>
      <div class="row"><button class="btn primary" id="pitch-btn" type="button">POST /generate-pitch</button></div>
      <h2 class="spaced">Explorador HTTP</h2>
      <div class="row">
        <button class="btn raw" data-path="/health" type="button">GET /health</button>
        <button class="btn raw" data-path="/api/v1/auth/me" type="button">GET /auth/me</button>
        <button class="btn raw" data-path="/api/v1/agents" type="button">GET /agents (admin)</button>
        <button class="btn raw" data-path="/api/v1/properties" type="button">GET /properties</button>
      </div>
    </div>
    <div class="card">
      <h2>Salida</h2>
      <div id="pitch-note" class="note">Sin peticiones.</div>
      <pre id="pitch-output">{}</pre>
    </div>
  </section>
</main>

<script nonce="__NONCE__">
(function () {
  "use strict";
  let token = null;
  let properties = [];
  // Los valores del contrato siguen en inglés; la interfaz los muestra en español.
  const STATUS_LABELS = { available: "Disponible", reserved: "Reservado", sold: "Vendido" };
  const statusLabel = (value) => STATUS_LABELS[value] || String(value);
  const ROLE_LABELS = { agent: "agente", admin: "admin" };
  const roleLabel = (value) => ROLE_LABELS[value] || String(value);

  const $ = (id) => document.getElementById(id);

  function setNote(id, kind, text) {
    const el = $(id);
    el.className = "note" + (kind ? " " + kind : "");
    el.textContent = text;
  }

  function show(id, data) {
    $(id).textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  }

  function headers(extra) {
    const h = Object.assign({}, extra || {});
    if (token) h["Authorization"] = "Bearer " + token;
    return h;
  }

  async function call(method, path, body) {
    const opts = { method: method, headers: headers(body ? { "Content-Type": "application/json" } : {}) };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    let data = null;
    const text = await res.text();
    try { data = text ? JSON.parse(text) : null; } catch (e) { data = text; }
    return { status: res.status, headers: res.headers, data: data };
  }

  function describe(status, data) {
    const code = data && data.error ? data.error.code : "";
    return "HTTP " + status + (code ? " " + code : "");
  }

  function decodeClaims(jwt) {
    try {
      const part = jwt.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
      const padded = part + "=".repeat((4 - (part.length % 4)) % 4);
      return JSON.parse(atob(padded));
    } catch (e) {
      return { error: "No se pudo decodificar el token." };
    }
  }

  function switchTab(name) {
    document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === "panel-" + name));
  }

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function fillSelect(id) {
    const select = $(id);
    select.replaceChildren();
    properties.forEach((p) => {
      const opt = el("option", "", "#" + p.id + " " + p.title + " (dueño: " + p.owner_agent_name + ")");
      opt.value = String(p.id);
      select.appendChild(opt);
    });
  }

  async function loadProperties() {
    const r = await call("GET", "/api/v1/properties");
    properties = Array.isArray(r.data) ? r.data : [];
    const grid = $("property-grid");
    grid.replaceChildren();
    if (properties.length === 0) {
      grid.appendChild(el("p", "empty", "No hay inmuebles todavía."));
    }
    properties.forEach((p) => {
      const card = el("div", "prop");
      card.appendChild(el("div", "meta", "#" + p.id + " " + p.city + ", " + statusLabel(p.status)));
      card.appendChild(el("h3", "", p.title));
      card.appendChild(el("p", "line", "USD " + Number(p.price).toLocaleString("es-GT") + ", " + p.bedrooms + " habitaciones"));
      card.appendChild(el("p", "line", "Dueño: " + p.owner_agent_name + " (#" + p.owner_agent_id + ")"));
      if (p.ai_pitch) card.appendChild(el("p", "pitch", p.ai_pitch));
      grid.appendChild(card);
    });
    fillSelect("authz-property");
    fillSelect("pitch-property");
  }

  async function login(ev) {
    ev.preventDefault();
    const email = $("login-email").value;
    const password = $("login-password").value;
    $("login-password").value = "";
    const r = await call("POST", "/api/v1/auth/token", { email: email, password: password });
    if (r.status === 200) {
      token = r.data.access_token;
      $("session-badge").className = "session on";
      $("session-badge").textContent = "Sesión: " + r.data.agent.name + " (" + roleLabel(r.data.agent.role) + ")";
      show("claims-box", decodeClaims(token));
      setNote("login-note", "ok", "HTTP 200. Token emitido; expira en " + r.data.expires_in_minutes + " minutos.");
    } else if (r.status === 429) {
      const wait = r.headers.get("Retry-After") || "?";
      setNote("login-note", "bad", describe(r.status, r.data) + ". Reintenta en " + wait + " segundos.");
    } else {
      setNote("login-note", "warn", describe(r.status, r.data) + ". " + (r.data && r.data.error ? r.data.error.message : ""));
    }
  }

  function logout() {
    token = null;
    $("session-badge").className = "session";
    $("session-badge").textContent = "Sin sesión";
    show("claims-box", "Sin token activo.");
    setNote("login-note", "", "Sin token: las rutas protegidas responden 401.");
  }

  async function createProperty(ev) {
    ev.preventDefault();
    const body = {
      title: $("new-title").value,
      city: $("new-city").value,
      price: Number($("new-price").value),
      bedrooms: Number($("new-bedrooms").value)
    };
    const r = await call("POST", "/api/v1/properties", body);
    if (r.status === 201) {
      setNote("create-note", "ok", "HTTP 201. Inmueble #" + r.data.id + " registrado a tu nombre.");
      await loadProperties();
    } else {
      setNote("create-note", "warn", describe(r.status, r.data));
    }
  }

  function authzVerdict(status) {
    if (status === 200 || status === 204) return ["ok", "Autorizado: eres dueño del inmueble o tienes rol admin."];
    if (status === 401) return ["warn", "Sin identidad: falta el token, expiró o no es válido. La identidad no está verificada."];
    if (status === 403) return ["bad", "Prohibido: el token es válido, pero el inmueble no es tuyo."];
    if (status === 404) return ["warn", "No encontrado: el inmueble no existe."];
    return ["", "Respuesta inesperada."];
  }

  async function patchStatus() {
    const id = $("authz-property").value;
    const r = await call("PATCH", "/api/v1/properties/" + encodeURIComponent(id) + "/status", { status: $("authz-status").value });
    const v = authzVerdict(r.status);
    setNote("authz-note", v[0], "HTTP " + r.status + ". " + v[1]);
    show("authz-output", r.data || {});
    if (r.status === 200) await loadProperties();
  }

  async function deleteProperty() {
    const id = $("authz-property").value;
    const r = await call("DELETE", "/api/v1/properties/" + encodeURIComponent(id));
    const v = authzVerdict(r.status);
    setNote("authz-note", v[0], "HTTP " + r.status + ". " + v[1]);
    show("authz-output", r.data || { status: "204 sin contenido" });
    if (r.status === 204) await loadProperties();
  }

  async function generatePitch() {
    const id = $("pitch-property").value;
    const r = await call("POST", "/api/v1/properties/" + encodeURIComponent(id) + "/generate-pitch");
    setNote("pitch-note", r.status === 200 ? "ok" : "warn", describe(r.status, r.data));
    show("pitch-output", r.data || {});
    if (r.status === 200) await loadProperties();
  }

  async function raw(path) {
    const r = await call("GET", path);
    setNote("pitch-note", r.status === 200 ? "ok" : "warn", "GET " + path + ": " + describe(r.status, r.data));
    show("pitch-output", r.data || {});
  }

  document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => switchTab(b.dataset.tab)));
  document.querySelectorAll(".raw").forEach((b) => b.addEventListener("click", () => raw(b.dataset.path)));
  $("login-form").addEventListener("submit", login);
  $("logout-btn").addEventListener("click", logout);
  $("create-form").addEventListener("submit", createProperty);
  $("reload-btn").addEventListener("click", loadProperties);
  $("patch-btn").addEventListener("click", patchStatus);
  $("delete-btn").addEventListener("click", deleteProperty);
  $("pitch-btn").addEventListener("click", generatePitch);
  loadProperties();
})();
</script>
</body>
</html>
"""


def render_console_html(nonce: str) -> str:
    """Devuelve la consola con el nonce de esta respuesta en <style> y <script>."""
    return _TEMPLATE.replace("__NONCE__", nonce)
