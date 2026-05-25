// ═══════════════════════════════════════════════════════════
// termini_admin.js — Osoba 3
// FZ-13 Sortiranje po tjednima
// FZ-19 Grupiranje po tjednima  
// FZ-15 Filteri (profesor, predmet, slobodni, moji)
// FZ-20 Moje prijave dashboard
// FZ-27 Pretraga po profesoru ili predmetu
// Koristi apiFetch(), getToken(), userFromToken() iz script.js
// ═══════════════════════════════════════════════════════════

// ── Stanje ──────────────────────────────────────────────────
let terminiData = [];
let editingTerminId = null;
let mojePrijaveData = [];
let prijavljeniTerminiIds = new Set();

// Filter stanje
let filterProfesor = "";
let filterPredmet = "";
let filterSamoSlobodni = false;
let filterSamoMoji = false;
let searchQuery = "";

// ── Init ────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  renderTerminiSection();
  renderAdminSection();
});

// ── Helperi ─────────────────────────────────────────────────
function safeApiFetch(path, options = {}) {
  if (typeof apiFetch !== "function") {
    throw new Error("apiFetch nije učitan.");
  }
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
function isAdminUser() { return normalizeRole(getCurrentTokenUser()?.role) === "admin"; }

function fmtDateTime(value) {
  if (!value) return "n/a";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("hr-HR", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function fmtDatum(value) {
  if (!value) return "n/a";
  const date = new Date(value);
  return date.toLocaleDateString("hr-HR", { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" });
}

function getTermId(term) { return term.term_id ?? term.id; }

function setTermsMessage(message, type = "info") {
  const el = document.querySelector("#terms-msg");
  if (!el) return;
  el.textContent = message;
  el.dataset.type = type;
}

function clearTermsMessage() {
  const el = document.querySelector("#terms-msg");
  if (!el) return;
  el.textContent = "";
  delete el.dataset.type;
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
  if (!isLoggedIn()) { normalizeMojePrijave([]); return; }
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

// ── Tjedni helper ────────────────────────────────────────────
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

// ── Filtriranje ──────────────────────────────────────────────
function filtrirajTermine(termini) {
  return termini.filter(t => {
    const termId = Number(getTermId(t));

    // Pretraga po profesoru ili predmetu
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchProf = String(t.professor_id).includes(q);
      const matchSubj = String(t.subject_id).includes(q);
      if (!matchProf && !matchSubj) return false;
    }

    // Filter po profesoru
    if (filterProfesor && String(t.professor_id) !== String(filterProfesor)) return false;

    // Filter po predmetu
    if (filterPredmet && String(t.subject_id) !== String(filterPredmet)) return false;

    // Samo slobodni
    if (filterSamoSlobodni && t._occ?.full) return false;

    // Samo moji
    if (filterSamoMoji && !prijavljeniTerminiIds.has(termId)) return false;

    return true;
  });
}

// ── TERMINI SEKCIJA ───────────────────────────────────────────
function renderTerminiSection() {
  const section = document.querySelector("#terms");
  if (!section) return;

  section.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Termini</h2>
        <p class="muted">Pregled dostupnih termina konzultacija i laboratorija.</p>
      </div>
      <div class="terms-actions">
        <button id="load-terms-button" type="button" class="secondary-button">Učitaj termine</button>
        <button id="load-my-registrations-button" type="button" class="secondary-button">Moje prijave</button>
      </div>
    </div>

    <div id="terms-msg" class="message-box" role="status"></div>

    <!-- Moje prijave dashboard -->
    <div id="moje-prijave" class="my-registrations-box">Moje prijave još nisu učitane.</div>

    <!-- Filteri i pretraga -->
    <div class="filters-bar" id="filters-bar" style="display:none">
      <div class="filter-search">
        <input type="text" id="search-input" placeholder="🔍 Pretraži po profesoru ili predmetu ID..."/>
      </div>
      <div class="filter-controls">
        <input type="number" id="filter-profesor" placeholder="Profesor ID" min="1"/>
        <input type="number" id="filter-predmet" placeholder="Predmet ID" min="1"/>
        <label class="filter-checkbox">
          <input type="checkbox" id="filter-slobodni"/> Samo slobodni
        </label>
        <label class="filter-checkbox">
          <input type="checkbox" id="filter-moji"/> Samo moji
        </label>
        <button type="button" class="secondary-button" onclick="resetFilters()">✕ Reset</button>
      </div>
    </div>

    <div id="termini-lista">Klikni gumb za učitavanje termina.</div>
  `;

  document.querySelector("#load-terms-button")?.addEventListener("click", ucitajTermine);
  document.querySelector("#load-my-registrations-button")?.addEventListener("click", prikaziMojePrijave);
}

async function ucitajTermine() {
  const lista = document.querySelector("#termini-lista");
  if (!lista) return;

  clearTermsMessage();
  lista.innerHTML = "<p class='muted'>Učitavanje...</p>";

  if (!isLoggedIn()) {
    lista.innerHTML = "<p class='muted'>Login je potreban za pregled termina.</p>";
    setTermsMessage("Prvo se loginaj.", "info");
    return;
  }

  try {
    terminiData = await safeApiFetch("/termini");
    await loadMojePrijaveSilently();
    await Promise.all(terminiData.map(async t => { t._occ = await loadOccupancyForTerm(t); }));

    // Prikaži filtere
    const filtersBar = document.querySelector("#filters-bar");
    if (filtersBar) filtersBar.style.display = "block";

    // Postavi event listenere za filtere
    setupFilterListeners();

    renderFilteredTermini();
    renderMojePrijave();
  } catch (error) {
    lista.innerHTML = `<p class="message-error">Greška: ${error.message}</p>`;
  }
}

function setupFilterListeners() {
  const searchInput = document.querySelector("#search-input");
  const filterProfesorEl = document.querySelector("#filter-profesor");
  const filterPredmetEl = document.querySelector("#filter-predmet");
  const filterSlobodniEl = document.querySelector("#filter-slobodni");
  const filterMojiEl = document.querySelector("#filter-moji");

  if (searchInput && !searchInput._listenerAdded) {
    searchInput.addEventListener("input", e => { searchQuery = e.target.value.trim(); renderFilteredTermini(); });
    searchInput._listenerAdded = true;
  }
  if (filterProfesorEl && !filterProfesorEl._listenerAdded) {
    filterProfesorEl.addEventListener("input", e => { filterProfesor = e.target.value.trim(); renderFilteredTermini(); });
    filterProfesorEl._listenerAdded = true;
  }
  if (filterPredmetEl && !filterPredmetEl._listenerAdded) {
    filterPredmetEl.addEventListener("input", e => { filterPredmet = e.target.value.trim(); renderFilteredTermini(); });
    filterPredmetEl._listenerAdded = true;
  }
  if (filterSlobodniEl && !filterSlobodniEl._listenerAdded) {
    filterSlobodniEl.addEventListener("change", e => { filterSamoSlobodni = e.target.checked; renderFilteredTermini(); });
    filterSlobodniEl._listenerAdded = true;
  }
  if (filterMojiEl && !filterMojiEl._listenerAdded) {
    filterMojiEl.addEventListener("change", e => { filterSamoMoji = e.target.checked; renderFilteredTermini(); });
    filterMojiEl._listenerAdded = true;
  }
}

function resetFilters() {
  filterProfesor = "";
  filterPredmet = "";
  filterSamoSlobodni = false;
  filterSamoMoji = false;
  searchQuery = "";

  const el = id => document.querySelector(`#${id}`);
  if (el("search-input")) el("search-input").value = "";
  if (el("filter-profesor")) el("filter-profesor").value = "";
  if (el("filter-predmet")) el("filter-predmet").value = "";
  if (el("filter-slobodni")) el("filter-slobodni").checked = false;
  if (el("filter-moji")) el("filter-moji").checked = false;

  renderFilteredTermini();
}

function renderFilteredTermini() {
  const lista = document.querySelector("#termini-lista");
  if (!lista) return;

  const filtered = filtrirajTermine(terminiData);

  if (!filtered.length) {
    lista.innerHTML = "<p class='muted'>Nema termina koji odgovaraju filterima.</p>";
    return;
  }

  // Grupiraj po tjednima i sortiraj kronološki
  const groups = groupByWeek(filtered);
  let html = "";

  for (const [weekKey, termini] of groups) {
    html += `
      <div class="week-group">
        <div class="week-header">${getWeekLabel(weekKey)}</div>
        <div class="termini-lista">
          ${termini.map(renderTerminCard).join("")}
        </div>
      </div>
    `;
  }

  lista.innerHTML = html;
}

function renderTerminCard(term) {
  const termId = Number(getTermId(term));
  const start = new Date(term.start_time);
  const end = new Date(term.end_time);
  const minutes = Math.round((end - start) / 60000);
  const occ = term._occ;
  const capacity = occ ? occ.capacity : "?";
  const registered = occ ? occ.registered_students : "?";
  const full = Boolean(occ?.full);
  const isRegistered = prijavljeniTerminiIds.has(termId);
  const pct = occ && occ.capacity > 0 ? Math.round((occ.registered_students / occ.capacity) * 100) : 0;
  const barColor = pct >= 100 ? "occ-red" : pct >= 70 ? "occ-yellow" : "occ-green";

  let actionButton = "";
  if (!isLoggedIn()) {
    actionButton = `<button type="button" disabled>Login potreban</button>`;
  } else if (isRegistered) {
    actionButton = `<button type="button" class="secondary-button" onclick="odjaviSeSTermina(${termId})">Odjavi se</button>`;
  } else {
    actionButton = `<button type="button" ${full ? "disabled" : ""} onclick="prijaviSeNaTermin(${termId})">${full ? "Termin je pun" : "Prijavi se"}</button>`;
  }

  return `
    <article class="termin-card ${isRegistered ? "is-registered" : ""}">
      <div class="termin-card-main">
        <div class="termin-card-header">
          <h3>Termin #${termId}</h3>
          ${isRegistered ? "<span class='registered-badge'>Prijavljen/a</span>" : ""}
        </div>
        <p class="muted">Prof. ID: <strong>${term.professor_id}</strong> &nbsp;·&nbsp; Predmet ID: <strong>${term.subject_id}</strong></p>
        <p>📅 ${fmtDateTime(term.start_time)} — ${fmtDateTime(term.end_time)}</p>
        <p>⏱ ${Number.isFinite(minutes) ? minutes : "?"} min</p>
        <div class="occ-wrap">
          <div class="occ-bar"><div class="occ-fill ${barColor}" style="width:${Math.min(pct,100)}%"></div></div>
          <span>${registered}/${capacity} ${full ? "· Popunjeno" : "· Slobodno"}</span>
        </div>
      </div>
      <div class="termin-card-actions">${actionButton}</div>
    </article>
  `;
}

// ── Prijava / Odjava ─────────────────────────────────────────
async function prijaviSeNaTermin(termId) {
  clearTermsMessage();
  try {
    await safeApiFetch(`/termini/${termId}/prijava`, { method: "POST" });
    setTermsMessage(`Uspješno si prijavljen/a na termin #${termId}.`, "ok");
    await ucitajTermine();
  } catch (error) {
    setTermsMessage(`Prijava nije uspjela: ${error.message}`, "error");
  }
}

async function odjaviSeSTermina(termId) {
  clearTermsMessage();
  try {
    await safeApiFetch(`/termini/${termId}/prijava`, { method: "DELETE" });
    setTermsMessage(`Uspješno si odjavljen/a s termina #${termId}.`, "ok");
    await ucitajTermine();
  } catch (error) {
    setTermsMessage(`Odjava nije uspjela: ${error.message}`, "error");
  }
}

// ── Moje prijave dashboard ───────────────────────────────────
async function prikaziMojePrijave() {
  clearTermsMessage();
  if (!isLoggedIn()) {
    setTermsMessage("Login je potreban.", "info");
    return;
  }
  try {
    const prijave = await safeApiFetch("/me/prijave");
    normalizeMojePrijave(prijave);
    renderMojePrijave();
  } catch (error) {
    setTermsMessage(`Greška: ${error.message}`, "error");
  }
}

function renderMojePrijave() {
  const container = document.querySelector("#moje-prijave");
  if (!container) return;

  if (!isLoggedIn()) {
    container.innerHTML = "<p class='muted'>Niste prijavljeni.</p>";
    return;
  }

  if (!mojePrijaveData.length) {
    container.innerHTML = `
      <div class="my-reg-header">
        <h3>📋 Moje prijave</h3>
      </div>
      <p class="muted">Trenutno nemaš aktivnih prijava.</p>
    `;
    return;
  }

  container.innerHTML = `
    <div class="my-reg-header">
      <h3>📋 Moje prijave <span class="badge-count">${mojePrijaveData.length}</span></h3>
    </div>
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
            <button type="button" class="btn-odjava" onclick="odjaviSeSTermina(${termId})">
              Odjavi se
            </button>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

// ── ADMIN SEKCIJA ────────────────────────────────────────────
function renderAdminSection() {
  const section = document.querySelector("#admin");
  if (!section) return;

  if (!isLoggedIn()) {
    section.innerHTML = `<h2>Admin — Upravljanje terminima</h2><p class="muted">Login je potreban za admin funkcionalnosti.</p>`;
    return;
  }

  if (!isAdminUser()) {
    section.innerHTML = `<h2>Admin — Upravljanje terminima</h2><p class="muted">Ova sekcija je dostupna samo administratorima.</p>`;
    return;
  }

  section.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Admin — Upravljanje terminima</h2>
        <p class="muted">Kreiranje, uređivanje i brisanje termina.</p>
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

    <div id="admin-termini-lista">Klikni "Osvježi" za učitavanje termina.</div>
  `;

  ucitajAdminTermine();
}

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
  if (!terminiData.length) {
    container.innerHTML = "<p class='muted'>Nema termina.</p>";
    return;
  }

  const sorted = [...terminiData].sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

  container.innerHTML = `
    <table class="termini-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Profesor ID</th>
          <th>Predmet ID</th>
          <th>Početak</th>
          <th>Kraj</th>
          <th>Popunjenost</th>
          <th>Akcije</th>
        </tr>
      </thead>
      <tbody>
        ${sorted.map(t => {
          const termId = getTermId(t);
          const occ = t._occ;
          return `
            <tr>
              <td>#${termId}</td>
              <td>${t.professor_id}</td>
              <td>${t.subject_id}</td>
              <td>${fmtDateTime(t.start_time)}</td>
              <td>${fmtDateTime(t.end_time)}</td>
              <td>${occ ? `${occ.registered_students}/${occ.capacity}` : "?"}</td>
              <td class="table-actions">
                <button type="button" class="secondary-button" onclick="otvoriFormuUredivanje(${termId})">Uredi</button>
                <button type="button" class="danger-button" onclick="obrisiTermin(${termId})">Briši</button>
              </td>
            </tr>
          `;
        }).join("")}
      </tbody>
    </table>
  `;
}

// ── Forma ────────────────────────────────────────────────────
function otvoriFormuKreiranje() {
  editingTerminId = null;
  document.querySelector("#forma-naslov").textContent = "Novi termin";
  document.querySelector("#forma-btn").textContent = "Kreiraj";
  ["f-prof","f-subj","f-start","f-end"].forEach(id => { document.querySelector(`#${id}`).value = ""; });
  document.querySelector("#termin-forma").style.display = "block";
}

function otvoriFormuUredivanje(id) {
  const t = terminiData.find(x => Number(getTermId(x)) === Number(id));
  if (!t) return;
  editingTerminId = id;
  document.querySelector("#forma-naslov").textContent = `Uredi termin #${id}`;
  document.querySelector("#forma-btn").textContent = "Spremi izmjene";
  document.querySelector("#f-prof").value = t.professor_id;
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
  const prof  = Number.parseInt(document.querySelector("#f-prof").value, 10);
  const subj  = Number.parseInt(document.querySelector("#f-subj").value, 10);
  const start = document.querySelector("#f-start").value;
  const end   = document.querySelector("#f-end").value;

  if (!prof || !subj) { prikaziAdminMsg("Profesor i predmet su obavezni.", "error"); return; }
  if (!start || !end)  { prikaziAdminMsg("Datum i vrijeme su obavezni.", "error"); return; }
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
    await ucitajTermine();
  } catch (error) {
    prikaziAdminMsg(`Greška: ${error.message}`, "error");
  }
}

async function obrisiTermin(id) {
  if (!confirm(`Obrisati termin #${id}?\n\nSve prijave bit će obrisane.`)) return;
  try {
    await safeApiFetch(`/termini/${id}`, { method: "DELETE" });
    prikaziAdminMsg(`Termin #${id} obrisan.`, "ok");
    await ucitajAdminTermine();
    await ucitajTermine();
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

// ── Eksponiranje za inline onclick ───────────────────────────
window.ucitajTermine = ucitajTermine;
window.prijaviSeNaTermin = prijaviSeNaTermin;
window.odjaviSeSTermina = odjaviSeSTermina;
window.prikaziMojePrijave = prikaziMojePrijave;
window.resetFilters = resetFilters;
window.ucitajAdminTermine = ucitajAdminTermine;
window.otvoriFormuKreiranje = otvoriFormuKreiranje;
window.otvoriFormuUredivanje = otvoriFormuUredivanje;
window.zatvoriFormu = zatvoriFormu;
window.spremiTermin = spremiTermin;
window.obrisiTermin = obrisiTermin;
