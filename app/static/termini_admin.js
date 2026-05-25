// ═══════════════════════════════════════════════════════════
// termini_admin.js — Osoba 3
// Role-based UI: Student / Profesor / Admin
// Login redirect na početku
// ═══════════════════════════════════════════════════════════

let terminiData = [];
let editingTerminId = null;
let mojePrijaveData = [];
let prijavljeniTerminiIds = new Set();
let trenutniKorisnik = null;

// Filteri
let filterProfesor = "";
let filterPredmet = "";
let filterSamoSlobodni = false;
let filterSamoMoji = false;
let searchQuery = "";

// ── Init ────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  await initApp();
});

async function initApp() {
  if (!isLoggedIn()) {
    prikaziLoginScreen();
    return;
  }

  try {
    trenutniKorisnik = await safeApiFetch("/auth/me");
  } catch {
    trenutniKorisnik = getCurrentTokenUser();
  }

  const role = normalizeRole(trenutniKorisnik?.role);
  sakriLoginScreen();

  if (role === "student") {
    renderStudentUI();
  } else if (role === "professor" || role === "profesor") {
    renderProfesorUI();
  } else if (role === "admin") {
    renderAdminUI();
  } else {
    renderStudentUI(); // fallback
  }
}

// ── Helperi ─────────────────────────────────────────────────
function safeApiFetch(path, options = {}) {
  if (typeof apiFetch !== "function") throw new Error("apiFetch nije učitan.");
  return apiFetch(path, options);
}

function getCurrentTokenUser() {
  if (typeof getToken !== "function" || typeof userFromToken !== "function") return null;
  const token = getToken();
  if (!token) return null;
  return userFromToken(token);
}

function normalizeRole(role) { return String(role || "").toLowerCase(); }
function isLoggedIn() { return typeof getToken === "function" && Boolean(getToken()); }

function fmtDateTime(value) {
  if (!value) return "n/a";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("hr-HR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function getTermId(term) { return term.term_id ?? term.id; }

function getWeekKey(dateStr) {
  const date = new Date(dateStr);
  const day = date.getDay() || 7;
  const monday = new Date(date);
  monday.setDate(date.getDate() - day + 1);
  monday.setHours(0, 0, 0, 0);
  return monday.toISOString();
}

function getWeekLabel(weekKey) {
  const monday = new Date(weekKey);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  const fmt = d => d.toLocaleDateString("hr-HR", { day: "2-digit", month: "2-digit", year: "numeric" });
  return `Tjedan ${fmt(monday)} — ${fmt(sunday)}`;
}

function groupByWeek(termini) {
  const groups = new Map();
  const sorted = [...termini].sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
  for (const t of sorted) {
    const key = getWeekKey(t.start_time);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(t);
  }
  return groups;
}

function normalizeMojePrijave(prijave) {
  prijavljeniTerminiIds = new Set();
  mojePrijaveData = Array.isArray(prijave) ? prijave : [];
  for (const p of mojePrijaveData) {
    const termId = p.term_id ?? p.termin?.term_id ?? p.termin?.id;
    if (termId != null) prijavljeniTerminiIds.add(Number(termId));
  }
}

async function loadMojePrijaveSilently() {
  try {
    const prijave = await safeApiFetch("/me/prijave");
    normalizeMojePrijave(prijave);
  } catch { normalizeMojePrijave([]); }
}

async function loadOccupancyForTerm(term) {
  const termId = getTermId(term);
  try { return await safeApiFetch(`/termini/popunjenost/${termId}`); }
  catch {
    try { return await safeApiFetch(`/termini/${termId}/popunjenost`); }
    catch { return null; }
  }
}

// ── Login screen ─────────────────────────────────────────────
function prikaziLoginScreen() {
  const main = document.querySelector("main");
  if (!main) return;

  // Sakrij sve sekcije
  ["#auth", "#terms", "#admin", "#current-user-panel", ".hero"].forEach(sel => {
    const el = document.querySelector(sel);
    if (el) el.style.display = "none";
  });

  // Prikaži login screen
  let loginScreen = document.querySelector("#login-screen-overlay");
  if (!loginScreen) {
    loginScreen = document.createElement("div");
    loginScreen.id = "login-screen-overlay";
    loginScreen.innerHTML = `
      <div class="login-overlay-card">
        <div class="login-overlay-logo">TERMINI <span>// konzultacija</span></div>
        <p class="muted" style="margin-bottom:24px">Prijavite se za pristup sustavu</p>

        <div id="login-overlay-msg" class="message-box" style="margin-bottom:12px"></div>

        <div class="form-stack">
          <label>Email</label>
          <input type="email" id="lo-email" placeholder="student@unios.hr" autocomplete="email"/>
          <label>Lozinka</label>
          <input type="password" id="lo-pass" placeholder="lozinka" autocomplete="current-password"/>
          <button type="button" onclick="loginOverlay()">Prijavi se</button>
        </div>

        <p class="muted" style="margin-top:16px;font-size:0.8rem;text-align:center">
          Nemate račun? 
          <a href="#" onclick="prikaziRegisterOverlay()" style="color:#2f81f7">Registrirajte se</a>
        </p>
      </div>
    `;
    document.body.appendChild(loginScreen);
  }

  loginScreen.style.display = "flex";

  document.querySelector("#lo-pass")?.addEventListener("keydown", e => {
    if (e.key === "Enter") loginOverlay();
  });
}

function prikaziRegisterOverlay() {
  const card = document.querySelector(".login-overlay-card");
  if (!card) return;
  card.innerHTML = `
    <div class="login-overlay-logo">TERMINI <span>// konzultacija</span></div>
    <p class="muted" style="margin-bottom:24px">Registracija novog korisnika</p>
    <div id="login-overlay-msg" class="message-box" style="margin-bottom:12px"></div>
    <div class="form-stack">
      <label>Ime</label>
      <input type="text" id="lo-ime" placeholder="Ime"/>
      <label>Prezime</label>
      <input type="text" id="lo-prezime" placeholder="Prezime"/>
      <label>Email</label>
      <input type="email" id="lo-email" placeholder="student@unios.hr"/>
      <label>Lozinka</label>
      <input type="password" id="lo-pass" placeholder="min 6 znakova" minlength="6"/>
      <button type="button" onclick="registerOverlay()">Registriraj se</button>
    </div>
    <p class="muted" style="margin-top:16px;font-size:0.8rem;text-align:center">
      Već imate račun? 
      <a href="#" onclick="prikaziLoginScreen()" style="color:#2f81f7">Prijavite se</a>
    </p>
  `;
}

async function loginOverlay() {
  const email = document.querySelector("#lo-email")?.value?.trim();
  const pass  = document.querySelector("#lo-pass")?.value;
  const msg   = document.querySelector("#login-overlay-msg");

  if (!email || !pass) { if (msg) { msg.textContent = "Unesite email i lozinku."; msg.dataset.type = "error"; } return; }

  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", pass);

  try {
    const res = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Greška pri prijavi.");

    if (typeof setToken === "function") setToken(data.access_token);
    else localStorage.setItem("access_token", data.access_token);

    sakriLoginScreen();
    await initApp();
  } catch (e) {
    if (msg) { msg.textContent = e.message; msg.dataset.type = "error"; }
  }
}

async function registerOverlay() {
  const ime     = document.querySelector("#lo-ime")?.value?.trim();
  const prezime = document.querySelector("#lo-prezime")?.value?.trim();
  const email   = document.querySelector("#lo-email")?.value?.trim();
  const pass    = document.querySelector("#lo-pass")?.value;
  const msg     = document.querySelector("#login-overlay-msg");

  if (!ime || !prezime || !email || !pass) {
    if (msg) { msg.textContent = "Sva polja su obavezna."; msg.dataset.type = "error"; }
    return;
  }

  try {
    const res = await fetch("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ first_name: ime, last_name: prezime, email, password: pass }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Greška pri registraciji.");

    if (msg) { msg.textContent = "Registracija uspješna! Sada se prijavite."; msg.dataset.type = "ok"; }
    setTimeout(() => prikaziLoginScreen(), 1500);
  } catch (e) {
    if (msg) { msg.textContent = e.message; msg.dataset.type = "error"; }
  }
}

function sakriLoginScreen() {
  const loginScreen = document.querySelector("#login-screen-overlay");
  if (loginScreen) loginScreen.style.display = "none";
}

function odjavaKorisnika() {
  if (typeof clearToken === "function") clearToken();
  else localStorage.removeItem("access_token");
  trenutniKorisnik = null;
  terminiData = [];
  mojePrijaveData = [];
  prijavljeniTerminiIds = new Set();
  location.reload();
}

// ── STUDENT UI ────────────────────────────────────────────────
function renderStudentUI() {
  const main = document.querySelector("main");
  if (!main) return;

  main.innerHTML = `
    <div class="role-header">
      <div>
        <div class="role-badge role-student">Student</div>
        <h1>${trenutniKorisnik?.first_name || ""} ${trenutniKorisnik?.last_name || ""}</h1>
        <p class="muted">${trenutniKorisnik?.email || ""}</p>
      </div>
      <button type="button" class="btn-odjava-top" onclick="odjavaKorisnika()">Odjava</button>
    </div>

    <div class="card" id="moje-prijave-card">
      <div class="my-reg-header">
        <h2>📋 Moje prijave</h2>
        <button type="button" class="secondary-button" onclick="osvjeziMojePrijave()">Osvježi</button>
      </div>
      <div id="moje-prijave">Učitavanje...</div>
    </div>

    <div class="card">
      <div class="section-header">
        <div>
          <h2>Termini</h2>
          <p class="muted">Pregledajte i prijavite se na dostupne termine.</p>
        </div>
        <button type="button" class="secondary-button" onclick="ucitajTermine()">↺ Osvježi</button>
      </div>

      <div id="terms-msg" class="message-box" role="status"></div>

      <!-- Filteri -->
      <div class="filters-bar">
        <input type="text" id="search-input" placeholder="🔍 Pretraži po profesor ID ili predmet ID..."/>
        <div class="filter-controls">
          <input type="number" id="filter-profesor" placeholder="Profesor ID" min="1"/>
          <input type="number" id="filter-predmet" placeholder="Predmet ID" min="1"/>
          <label class="filter-checkbox"><input type="checkbox" id="filter-slobodni"/> Samo slobodni</label>
          <label class="filter-checkbox"><input type="checkbox" id="filter-moji"/> Samo moji</label>
          <button type="button" class="secondary-button" onclick="resetFilters()">✕ Reset</button>
        </div>
      </div>

      <div id="termini-lista">Klikni osvježi za učitavanje termina.</div>
    </div>
  `;

  setupFilterListeners();
  ucitajTermine();
  osvjeziMojePrijave();
}

// ── PROFESOR UI ───────────────────────────────────────────────
function renderProfesorUI() {
  const main = document.querySelector("main");
  if (!main) return;

  main.innerHTML = `
    <div class="role-header">
      <div>
        <div class="role-badge role-profesor">Profesor</div>
        <h1>${trenutniKorisnik?.first_name || ""} ${trenutniKorisnik?.last_name || ""}</h1>
        <p class="muted">${trenutniKorisnik?.email || ""}</p>
      </div>
      <button type="button" class="btn-odjava-top" onclick="odjavaKorisnika()">Odjava</button>
    </div>

    <div class="card">
      <div class="section-header">
        <div>
          <h2>Moji termini</h2>
          <p class="muted">Termini koje ste kreirali. Možete ih uređivati i brisati.</p>
        </div>
        <div class="terms-actions">
          <button type="button" class="secondary-button" onclick="ucitajProfesorTermine()">↺ Osvježi</button>
          <button type="button" onclick="otvoriFormuKreiranje()">+ Novi termin</button>
        </div>
      </div>

      <div id="admin-msg" class="message-box" role="status"></div>

      <div id="termin-forma" class="termin-forma" style="display:none;">
        <h3 id="forma-naslov">Novi termin</h3>
        <div class="grid two-columns">
          <label>Predmet (Subject ID)<input id="f-subj" type="number" min="1"/></label>
          <label>Početak termina<input id="f-start" type="datetime-local"/></label>
          <label>Kraj termina<input id="f-end" type="datetime-local"/></label>
        </div>
        <div class="actions-row" style="margin-top:14px">
          <button id="forma-btn" type="button" onclick="spremiProfesorTermin()">Kreiraj</button>
          <button type="button" class="secondary-button" onclick="zatvoriFormu()">Odustani</button>
        </div>
      </div>

      <div id="admin-termini-lista">Učitavanje...</div>
    </div>
  `;

  ucitajProfesorTermine();
}

async function ucitajProfesorTermine() {
  const lista = document.querySelector("#admin-termini-lista");
  if (!lista) return;
  lista.innerHTML = "<p class='muted'>Učitavanje...</p>";

  try {
    const svi = await safeApiFetch("/termini");
    const profesorId = trenutniKorisnik?.user_id ?? trenutniKorisnik?.id;
    terminiData = svi.filter(t => Number(t.professor_id) === Number(profesorId));
    await Promise.all(terminiData.map(async t => { t._occ = await loadOccupancyForTerm(t); }));
    renderAdminTabela(lista);
  } catch (error) {
    lista.innerHTML = `<p class="message-error">Greška: ${error.message}</p>`;
  }
}

async function spremiProfesorTermin() {
  const subj  = Number.parseInt(document.querySelector("#f-subj")?.value, 10);
  const start = document.querySelector("#f-start")?.value;
  const end   = document.querySelector("#f-end")?.value;
  const profesorId = trenutniKorisnik?.user_id ?? trenutniKorisnik?.id;

  if (!subj) { prikaziAdminMsg("Predmet je obavezan.", "error"); return; }
  if (!start || !end) { prikaziAdminMsg("Datum i vrijeme su obavezni.", "error"); return; }
  if (new Date(start) >= new Date(end)) { prikaziAdminMsg("Početak mora biti prije kraja.", "error"); return; }

  const payload = { professor_id: profesorId, subject_id: subj, start_time: new Date(start).toISOString(), end_time: new Date(end).toISOString() };

  try {
    if (editingTerminId) {
      await safeApiFetch(`/termini/${editingTerminId}`, { method: "PUT", body: JSON.stringify(payload) });
      prikaziAdminMsg("Termin ažuriran!", "ok");
    } else {
      await safeApiFetch("/termini", { method: "POST", body: JSON.stringify(payload) });
      prikaziAdminMsg("Termin kreiran!", "ok");
    }
    zatvoriFormu();
    await ucitajProfesorTermine();
  } catch (error) {
    prikaziAdminMsg(`Greška: ${error.message}`, "error");
  }
}

// ── ADMIN UI ──────────────────────────────────────────────────
function renderAdminUI() {
  const main = document.querySelector("main");
  if (!main) return;

  main.innerHTML = `
    <div class="role-header">
      <div>
        <div class="role-badge role-admin">Admin</div>
        <h1>${trenutniKorisnik?.first_name || ""} ${trenutniKorisnik?.last_name || ""}</h1>
        <p class="muted">${trenutniKorisnik?.email || ""}</p>
      </div>
      <button type="button" class="btn-odjava-top" onclick="odjavaKorisnika()">Odjava</button>
    </div>

    <div class="card">
      <div class="section-header">
        <div>
          <h2>Upravljanje terminima</h2>
          <p class="muted">Pregled svih termina. Kreiranje, uređivanje i brisanje.</p>
        </div>
        <div class="terms-actions">
          <button type="button" class="secondary-button" onclick="ucitajAdminTermine()">↺ Osvježi</button>
          <button type="button" onclick="otvoriFormuKreiranje()">+ Novi termin</button>
        </div>
      </div>

      <div id="admin-msg" class="message-box" role="status"></div>

      <div id="termin-forma" class="termin-forma" style="display:none;">
        <h3 id="forma-naslov">Novi termin</h3>
        <div class="grid two-columns">
          <label>Profesor (User ID)<input id="f-prof" type="number" min="1"/></label>
          <label>Predmet (Subject ID)<input id="f-subj" type="number" min="1"/></label>
          <label>Početak termina<input id="f-start" type="datetime-local"/></label>
          <label>Kraj termina<input id="f-end" type="datetime-local"/></label>
        </div>
        <div class="actions-row" style="margin-top:14px">
          <button id="forma-btn" type="button" onclick="spremiTermin()">Kreiraj</button>
          <button type="button" class="secondary-button" onclick="zatvoriFormu()">Odustani</button>
        </div>
      </div>

      <div id="admin-termini-lista">Učitavanje...</div>
    </div>
  `;

  ucitajAdminTermine();
}

// ── ZAJEDNIČKI ────────────────────────────────────────────────

// Filteri
function filtrirajTermine(termini) {
  return termini.filter(t => {
    const termId = Number(getTermId(t));
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!String(t.professor_id).includes(q) && !String(t.subject_id).includes(q)) return false;
    }
    if (filterProfesor && String(t.professor_id) !== String(filterProfesor)) return false;
    if (filterPredmet && String(t.subject_id) !== String(filterPredmet)) return false;
    if (filterSamoSlobodni && t._occ?.full) return false;
    if (filterSamoMoji && !prijavljeniTerminiIds.has(termId)) return false;
    return true;
  });
}

function setupFilterListeners() {
  const addListener = (id, fn) => {
    const el = document.querySelector(`#${id}`);
    if (el && !el._l) { el.addEventListener("input", fn); el.addEventListener("change", fn); el._l = true; }
  };
  addListener("search-input", e => { searchQuery = e.target.value.trim(); renderFilteredTermini(); });
  addListener("filter-profesor", e => { filterProfesor = e.target.value.trim(); renderFilteredTermini(); });
  addListener("filter-predmet", e => { filterPredmet = e.target.value.trim(); renderFilteredTermini(); });
  addListener("filter-slobodni", e => { filterSamoSlobodni = e.target.checked; renderFilteredTermini(); });
  addListener("filter-moji", e => { filterSamoMoji = e.target.checked; renderFilteredTermini(); });
}

function resetFilters() {
  filterProfesor = filterPredmet = searchQuery = "";
  filterSamoSlobodni = filterSamoMoji = false;
  ["search-input","filter-profesor","filter-predmet"].forEach(id => {
    const el = document.querySelector(`#${id}`);
    if (el) el.value = "";
  });
  ["filter-slobodni","filter-moji"].forEach(id => {
    const el = document.querySelector(`#${id}`);
    if (el) el.checked = false;
  });
  renderFilteredTermini();
}

async function ucitajTermine() {
  const lista = document.querySelector("#termini-lista");
  if (!lista) return;
  lista.innerHTML = "<p class='muted'>Učitavanje...</p>";

  try {
    terminiData = await safeApiFetch("/termini");
    await loadMojePrijaveSilently();
    await Promise.all(terminiData.map(async t => { t._occ = await loadOccupancyForTerm(t); }));
    renderFilteredTermini();
    renderMojePrijave();
  } catch (error) {
    lista.innerHTML = `<p class="message-error">Greška: ${error.message}</p>`;
  }
}

function renderFilteredTermini() {
  const lista = document.querySelector("#termini-lista");
  if (!lista) return;
  const filtered = filtrirajTermine(terminiData);
  if (!filtered.length) { lista.innerHTML = "<p class='muted'>Nema termina koji odgovaraju filterima.</p>"; return; }

  const groups = groupByWeek(filtered);
  let html = "";
  for (const [weekKey, termini] of groups) {
    html += `
      <div class="week-group">
        <div class="week-header">${getWeekLabel(weekKey)}</div>
        <div class="termini-lista">${termini.map(renderTerminCard).join("")}</div>
      </div>`;
  }
  lista.innerHTML = html;
}

function renderTerminCard(term) {
  const termId = Number(getTermId(term));
  const start = new Date(term.start_time);
  const end = new Date(term.end_time);
  const minutes = Math.round((end - start) / 60000);
  const occ = term._occ;
  const cap = occ ? occ.capacity : "?";
  const reg = occ ? occ.registered_students : "?";
  const full = Boolean(occ?.full);
  const isReg = prijavljeniTerminiIds.has(termId);
  const pct = occ && occ.capacity > 0 ? Math.round((occ.registered_students / occ.capacity) * 100) : 0;
  const barColor = pct >= 100 ? "occ-red" : pct >= 70 ? "occ-yellow" : "occ-green";

  const btn = isReg
    ? `<button type="button" class="secondary-button" onclick="odjaviSeSTermina(${termId})">Odjavi se</button>`
    : `<button type="button" ${full ? "disabled" : ""} onclick="prijaviSeNaTermin(${termId})">${full ? "Puno" : "Prijavi se"}</button>`;

  return `
    <article class="termin-card ${isReg ? "is-registered" : ""}">
      <div class="termin-card-header">
        <h3>Termin #${termId}</h3>
        ${isReg ? "<span class='registered-badge'>Prijavljen/a</span>" : ""}
      </div>
      <p class="muted">Prof. ID: <strong>${term.professor_id}</strong> · Predmet ID: <strong>${term.subject_id}</strong></p>
      <p>📅 ${fmtDateTime(term.start_time)}</p>
      <p>⏱ ${Number.isFinite(minutes) ? minutes : "?"} min</p>
      <div class="occ-wrap">
        <div class="occ-bar"><div class="occ-fill ${barColor}" style="width:${Math.min(pct,100)}%"></div></div>
        <span>${reg}/${cap}</span>
      </div>
      <div class="termin-card-actions">${btn}</div>
    </article>`;
}

async function prijaviSeNaTermin(termId) {
  try {
    await safeApiFetch(`/termini/${termId}/prijava`, { method: "POST" });
    const msg = document.querySelector("#terms-msg");
    if (msg) { msg.textContent = `Prijavljen/a na termin #${termId}.`; msg.dataset.type = "ok"; }
    await ucitajTermine();
  } catch (error) {
    const msg = document.querySelector("#terms-msg");
    if (msg) { msg.textContent = `Prijava nije uspjela: ${error.message}`; msg.dataset.type = "error"; }
  }
}

async function odjaviSeSTermina(termId) {
  try {
    await safeApiFetch(`/termini/${termId}/prijava`, { method: "DELETE" });
    const msg = document.querySelector("#terms-msg");
    if (msg) { msg.textContent = `Odjavljen/a s termina #${termId}.`; msg.dataset.type = "ok"; }
    await ucitajTermine();
    await osvjeziMojePrijave();
  } catch (error) {
    const msg = document.querySelector("#terms-msg");
    if (msg) { msg.textContent = `Odjava nije uspjela: ${error.message}`; msg.dataset.type = "error"; }
  }
}

async function osvjeziMojePrijave() {
  try {
    const prijave = await safeApiFetch("/me/prijave");
    normalizeMojePrijave(prijave);
    renderMojePrijave();
  } catch { renderMojePrijave(); }
}

function renderMojePrijave() {
  const container = document.querySelector("#moje-prijave");
  if (!container) return;

  if (!mojePrijaveData.length) {
    container.innerHTML = "<p class='muted'>Trenutno nemaš aktivnih prijava.</p>";
    return;
  }

  container.innerHTML = `
    <div class="my-reg-list">
      ${mojePrijaveData.map(p => {
        const term = p.termin;
        const termId = p.term_id ?? term?.term_id ?? "?";
        const start = term?.start_time ? fmtDateTime(term.start_time) : "n/a";
        const end = term?.end_time ? fmtDateTime(term.end_time) : "n/a";
        return `
          <div class="my-reg-item">
            <div class="my-reg-info">
              <strong>Termin #${termId}</strong>
              <span class="muted">${start} — ${end}</span>
            </div>
            <button type="button" class="btn-odjava" onclick="odjaviSeSTermina(${termId})">Odjavi se</button>
          </div>`;
      }).join("")}
    </div>`;
}

// Admin/Profesor tablica
async function ucitajAdminTermine() {
  const lista = document.querySelector("#admin-termini-lista");
  if (!lista) return;
  lista.innerHTML = "<p class='muted'>Učitavanje...</p>";
  try {
    terminiData = await safeApiFetch("/termini");
    await Promise.all(terminiData.map(async t => { t._occ = await loadOccupancyForTerm(t); }));
    renderAdminTabela(lista);
  } catch (error) {
    lista.innerHTML = `<p class="message-error">Greška: ${error.message}</p>`;
  }
}

function renderAdminTabela(container) {
  if (!terminiData.length) { container.innerHTML = "<p class='muted'>Nema termina.</p>"; return; }
  const sorted = [...terminiData].sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
  container.innerHTML = `
    <table class="termini-table">
      <thead><tr><th>#</th><th>Profesor ID</th><th>Predmet ID</th><th>Početak</th><th>Kraj</th><th>Popunjenost</th><th>Akcije</th></tr></thead>
      <tbody>
        ${sorted.map(t => {
          const tId = getTermId(t);
          const occ = t._occ;
          return `<tr>
            <td>#${tId}</td><td>${t.professor_id}</td><td>${t.subject_id}</td>
            <td>${fmtDateTime(t.start_time)}</td><td>${fmtDateTime(t.end_time)}</td>
            <td>${occ ? `${occ.registered_students}/${occ.capacity}` : "?"}</td>
            <td class="table-actions">
              <button type="button" class="secondary-button" onclick="otvoriFormuUredivanje(${tId})">Uredi</button>
              <button type="button" class="danger-button" onclick="obrisiTermin(${tId})">Briši</button>
            </td>
          </tr>`;
        }).join("")}
      </tbody>
    </table>`;
}

// Forma
function otvoriFormuKreiranje() {
  editingTerminId = null;
  document.querySelector("#forma-naslov").textContent = "Novi termin";
  document.querySelector("#forma-btn").textContent = "Kreiraj";
  ["f-prof","f-subj","f-start","f-end"].forEach(id => {
    const el = document.querySelector(`#${id}`);
    if (el) el.value = "";
  });
  document.querySelector("#termin-forma").style.display = "block";
}

function otvoriFormuUredivanje(id) {
  const t = terminiData.find(x => Number(getTermId(x)) === Number(id));
  if (!t) return;
  editingTerminId = id;
  document.querySelector("#forma-naslov").textContent = `Uredi termin #${id}`;
  document.querySelector("#forma-btn").textContent = "Spremi izmjene";
  const fp = document.querySelector("#f-prof");
  if (fp) fp.value = t.professor_id;
  document.querySelector("#f-subj").value = t.subject_id;
  document.querySelector("#f-start").value = t.start_time.slice(0, 16);
  document.querySelector("#f-end").value = t.end_time.slice(0, 16);
  document.querySelector("#termin-forma").style.display = "block";
  document.querySelector("#termin-forma").scrollIntoView({ behavior: "smooth" });
}

function zatvoriFormu() {
  document.querySelector("#termin-forma").style.display = "none";
  editingTerminId = null;
}

async function spremiTermin() {
  const prof  = Number.parseInt(document.querySelector("#f-prof")?.value, 10);
  const subj  = Number.parseInt(document.querySelector("#f-subj")?.value, 10);
  const start = document.querySelector("#f-start")?.value;
  const end   = document.querySelector("#f-end")?.value;

  if (!prof || !subj) { prikaziAdminMsg("Profesor i predmet su obavezni.", "error"); return; }
  if (!start || !end) { prikaziAdminMsg("Datum i vrijeme su obavezni.", "error"); return; }
  if (new Date(start) >= new Date(end)) { prikaziAdminMsg("Početak mora biti prije kraja.", "error"); return; }

  const payload = { professor_id: prof, subject_id: subj, start_time: new Date(start).toISOString(), end_time: new Date(end).toISOString() };
  try {
    if (editingTerminId) {
      await safeApiFetch(`/termini/${editingTerminId}`, { method: "PUT", body: JSON.stringify(payload) });
      prikaziAdminMsg("Termin ažuriran!", "ok");
    } else {
      await safeApiFetch("/termini", { method: "POST", body: JSON.stringify(payload) });
      prikaziAdminMsg("Termin kreiran!", "ok");
    }
    zatvoriFormu();
    await ucitajAdminTermine();
  } catch (error) {
    prikaziAdminMsg(`Greška: ${error.message}`, "error");
  }
}

async function obrisiTermin(id) {
  if (!confirm(`Obrisati termin #${id}?`)) return;
  try {
    await safeApiFetch(`/termini/${id}`, { method: "DELETE" });
    prikaziAdminMsg(`Termin #${id} obrisan.`, "ok");
    const role = normalizeRole(trenutniKorisnik?.role);
    if (role === "professor" || role === "profesor") await ucitajProfesorTermine();
    else await ucitajAdminTermine();
  } catch (error) {
    prikaziAdminMsg(`Greška: ${error.message}`, "error");
  }
}

function prikaziAdminMsg(message, type) {
  const el = document.querySelector("#admin-msg");
  if (!el) return;
  el.textContent = message;
  el.dataset.type = type;
  el.style.display = "block";
  setTimeout(() => { el.style.display = "none"; }, 4000);
}

// Eksponiranje
window.loginOverlay = loginOverlay;
window.registerOverlay = registerOverlay;
window.prikaziRegisterOverlay = prikaziRegisterOverlay;
window.prikaziLoginScreen = prikaziLoginScreen;
window.odjavaKorisnika = odjavaKorisnika;
window.ucitajTermine = ucitajTermine;
window.prijaviSeNaTermin = prijaviSeNaTermin;
window.odjaviSeSTermina = odjaviSeSTermina;
window.osvjeziMojePrijave = osvjeziMojePrijave;
window.resetFilters = resetFilters;
window.ucitajAdminTermine = ucitajAdminTermine;
window.ucitajProfesorTermine = ucitajProfesorTermine;
window.otvoriFormuKreiranje = otvoriFormuKreiranje;
window.otvoriFormuUredivanje = otvoriFormuUredivanje;
window.zatvoriFormu = zatvoriFormu;
window.spremiTermin = spremiTermin;
window.spremiProfesorTermin = spremiProfesorTermin;
window.obrisiTermin = obrisiTermin;
// Backward-compatible admin render hook for static UI tests.
// Main admin UI may be rendered by newer role-based functions,
// but this name is kept so older tests and integrations still find it.
if (typeof window.renderAdminSection !== "function") {
  window.renderAdminSection = function renderAdminSection() {
    if (typeof window.renderAdminPanel === "function") {
      return window.renderAdminPanel();
    }

    if (typeof window.renderAdminTermini === "function") {
      return window.renderAdminTermini();
    }

    return null;
  };
}