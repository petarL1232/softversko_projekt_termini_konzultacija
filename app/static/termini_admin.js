// ═══════════════════════════════════════════════════════════
// termini_admin.js — Osoba 3: Admin UI za termine
// + dodatak za Osobu 4: student prijava/odjava na termin
// Koristi apiFetch(), getToken() i userFromToken() iz script.js (Petar L, Osoba 1)
// ═══════════════════════════════════════════════════════════

// ── Stanje ──────────────────────────────────────────────────
let terminiData = [];
let editingTerminId = null;
let mojePrijaveData = [];
let prijavljeniTerminiIds = new Set();

// ── Init ────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  renderTerminiSection();
  renderAdminSection();
});

// ── Helperi ─────────────────────────────────────────────────
function safeApiFetch(path, options = {}) {
  if (typeof apiFetch !== "function") {
    throw new Error("apiFetch nije učitan. Provjeri redoslijed script tagova.");
  }

  return apiFetch(path, options);
}

function getCurrentTokenUser() {
  if (typeof getToken !== "function" || typeof userFromToken !== "function") {
    return null;
  }

  const token = getToken();
  if (!token) {
    return null;
  }

  return userFromToken(token);
}

function normalizeRole(role) {
  return String(role || "").toLowerCase();
}

function isLoggedIn() {
  return typeof getToken === "function" && Boolean(getToken());
}

function isAdminUser() {
  const user = getCurrentTokenUser();
  return normalizeRole(user?.role) === "admin";
}

function fmtDateTime(value) {
  if (!value) {
    return "n/a";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString("hr-HR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getTermId(term) {
  return term.term_id ?? term.id;
}

function setTermsMessage(message, type = "info") {
  const el = document.querySelector("#terms-msg");
  if (!el) {
    return;
  }

  el.textContent = message;
  el.dataset.type = type;
}

function clearTermsMessage() {
  const el = document.querySelector("#terms-msg");
  if (!el) {
    return;
  }

  el.textContent = "";
  delete el.dataset.type;
}

function normalizeMojePrijave(prijave) {
  prijavljeniTerminiIds = new Set();
  mojePrijaveData = Array.isArray(prijave) ? prijave : [];

  for (const prijava of mojePrijaveData) {
    const termId = prijava.term_id ?? prijava.termin?.term_id ?? prijava.termin?.id;
    if (termId !== undefined && termId !== null) {
      prijavljeniTerminiIds.add(Number(termId));
    }
  }
}

async function loadMojePrijaveSilently() {
  if (!isLoggedIn()) {
    normalizeMojePrijave([]);
    return;
  }

  try {
    const prijave = await safeApiFetch("/me/prijave");
    normalizeMojePrijave(prijave);
  } catch {
    normalizeMojePrijave([]);
  }
}

async function loadOccupancyForTerm(term) {
  const termId = getTermId(term);

  try {
    return await safeApiFetch(`/termini/popunjenost/${termId}`);
  } catch {
    try {
      return await safeApiFetch(`/termini/${termId}/popunjenost`);
    } catch {
      return null;
    }
  }
}

// ── Termini sekcija (student prijava/odjava) ────────────────
function renderTerminiSection() {
  const section = document.querySelector("#terms");
  if (!section) {
    return;
  }

  section.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Termini</h2>
        <p class="muted">
          Pregled dostupnih termina konzultacija i laboratorija.
          Student se ovdje može prijaviti i odjaviti s termina.
        </p>
      </div>
      <div class="terms-actions">
        <button id="load-terms-button" type="button" class="secondary-button">Učitaj termine</button>
        <button id="load-my-registrations-button" type="button" class="secondary-button">Moje prijave</button>
      </div>
    </div>

    <div id="terms-msg" class="message-box" role="status"></div>
    <div id="moje-prijave" class="my-registrations-box">Moje prijave još nisu učitane.</div>
    <div id="termini-lista" class="termini-lista">Klikni gumb za učitavanje termina.</div>
  `;

  document
    .querySelector("#load-terms-button")
    ?.addEventListener("click", ucitajTermine);
  document
    .querySelector("#load-my-registrations-button")
    ?.addEventListener("click", prikaziMojePrijave);
}

async function ucitajTermine() {
  const lista = document.querySelector("#termini-lista");
  if (!lista) {
    return;
  }

  clearTermsMessage();
  lista.innerHTML = "<p class='muted'>Učitavanje...</p>";

  if (!isLoggedIn()) {
    lista.innerHTML = "<p class='muted'>Login je potreban za pregled i prijavu na termine.</p>";
    setTermsMessage("Prvo se loginaj kao student ili admin.", "info");
    return;
  }

  try {
    terminiData = await safeApiFetch("/termini");
    await loadMojePrijaveSilently();

    await Promise.all(
      terminiData.map(async (term) => {
        term._occ = await loadOccupancyForTerm(term);
      }),
    );

    renderTerminiLista(lista);
    renderMojePrijave();
  } catch (error) {
    lista.innerHTML = `<p class="message-error">Greška: ${error.message}</p>`;
  }
}

function renderTerminiLista(container) {
  if (!terminiData.length) {
    container.innerHTML = "<p class='muted'>Nema dostupnih termina.</p>";
    return;
  }

  container.innerHTML = terminiData.map(renderTerminCard).join("");
}

function renderTerminCard(term) {
  const termId = Number(getTermId(term));
  const start = new Date(term.start_time);
  const end = new Date(term.end_time);
  const minutes = Math.round((end - start) / 60000);
  const occupancy = term._occ;
  const capacity = occupancy ? occupancy.capacity : "?";
  const registered = occupancy ? occupancy.registered_students : "?";
  const full = Boolean(occupancy?.full);
  const isRegistered = prijavljeniTerminiIds.has(termId);

  let actionButton = "";
  if (!isLoggedIn()) {
    actionButton = `<button type="button" disabled>Login potreban</button>`;
  } else if (isRegistered) {
    actionButton = `
      <button type="button" class="secondary-button" onclick="odjaviSeSTermina(${termId})">
        Odjavi se
      </button>
    `;
  } else {
    actionButton = `
      <button type="button" ${full ? "disabled" : ""} onclick="prijaviSeNaTermin(${termId})">
        ${full ? "Termin je pun" : "Prijavi se"}
      </button>
    `;
  }

  return `
    <article class="termin-card ${isRegistered ? "is-registered" : ""}">
      <div class="termin-card-main">
        <h3>Termin #${termId}</h3>
        <p class="muted">Profesor ID: ${term.professor_id} · Predmet ID: ${term.subject_id}</p>
        <p><strong>Početak:</strong> ${fmtDateTime(term.start_time)}</p>
        <p><strong>Kraj:</strong> ${fmtDateTime(term.end_time)}</p>
        <p><strong>Trajanje:</strong> ${Number.isFinite(minutes) ? minutes : "?"} min</p>
        <p><strong>Popunjenost:</strong> ${registered}/${capacity}</p>
        <p><strong>Status:</strong> ${full ? "Popunjeno" : "Ima slobodnih mjesta"}</p>
        ${isRegistered ? "<p class='registered-badge'>Već si prijavljen/a na ovaj termin.</p>" : ""}
      </div>
      <div class="termin-card-actions">
        ${actionButton}
      </div>
    </article>
  `;
}

async function prijaviSeNaTermin(termId) {
  clearTermsMessage();

  try {
    await safeApiFetch(`/termini/${termId}/prijava`, {
      method: "POST",
    });
    setTermsMessage(`Uspješno si prijavljen/a na termin #${termId}.`, "ok");
    await ucitajTermine();
  } catch (error) {
    setTermsMessage(`Prijava nije uspjela: ${error.message}`, "error");
  }
}

async function odjaviSeSTermina(termId) {
  clearTermsMessage();

  try {
    await safeApiFetch(`/termini/${termId}/prijava`, {
      method: "DELETE",
    });
    setTermsMessage(`Uspješno si odjavljen/a s termina #${termId}.`, "ok");
    await ucitajTermine();
  } catch (error) {
    setTermsMessage(`Odjava nije uspjela: ${error.message}`, "error");
  }
}

async function prikaziMojePrijave() {
  clearTermsMessage();

  if (!isLoggedIn()) {
    setTermsMessage("Login je potreban za prikaz mojih prijava.", "info");
    renderMojePrijave();
    return;
  }

  try {
    const prijave = await safeApiFetch("/me/prijave");
    normalizeMojePrijave(prijave);
    renderMojePrijave();
  } catch (error) {
    setTermsMessage(`Moje prijave nisu dostupne: ${error.message}`, "error");
  }
}

function renderMojePrijave() {
  const container = document.querySelector("#moje-prijave");
  if (!container) {
    return;
  }

  if (!isLoggedIn()) {
    container.innerHTML = "<p class='muted'>Niste prijavljeni.</p>";
    return;
  }

  if (!mojePrijaveData.length) {
    container.innerHTML = "<p class='muted'>Trenutno nemaš aktivnih prijava.</p>";
    return;
  }

  container.innerHTML = `
    <h3>Moje prijave</h3>
    <ul class="registrations-list">
      ${mojePrijaveData.map(renderMojaPrijava).join("")}
    </ul>
  `;
}

function renderMojaPrijava(prijava) {
  const term = prijava.termin;
  const termId = prijava.term_id ?? term?.term_id ?? "?";
  const start = term?.start_time ? fmtDateTime(term.start_time) : "n/a";

  return `
    <li>
      <strong>Termin #${termId}</strong>
      <span class="muted">· ${start}</span>
      <button type="button" class="link-button" onclick="odjaviSeSTermina(${termId})">
        Odjavi se
      </button>
    </li>
  `;
}

// ── Admin sekcija (samo admin) ───────────────────────────────
function renderAdminSection() {
  const section = document.querySelector("#admin");
  if (!section) {
    return;
  }

  if (!isLoggedIn()) {
    section.innerHTML = `
      <h2>Admin — Upravljanje terminima</h2>
      <p class="muted">Login je potreban za admin funkcionalnosti.</p>
    `;
    return;
  }

  if (!isAdminUser()) {
    section.innerHTML = `
      <h2>Admin — Upravljanje terminima</h2>
      <p class="muted">Ova sekcija je dostupna samo administratorima.</p>
    `;
    return;
  }

  section.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Admin — Upravljanje terminima</h2>
        <p class="muted">Kreiranje, uređivanje i brisanje termina. Dostupno samo adminima.</p>
      </div>
      <div class="terms-actions">
        <button type="button" class="secondary-button" onclick="ucitajAdminTermine()">Osvježi</button>
        <button type="button" onclick="otvoriFormuKreiranje()">+ Novi termin</button>
      </div>
    </div>

    <div id="admin-msg" class="message-box" role="status"></div>

    <div id="termin-forma" class="termin-forma" style="display:none;">
      <h3 id="forma-naslov">Novi termin</h3>
      <div class="grid two-columns">
        <label>
          Profesor (User ID)
          <input id="f-prof" type="number" min="1" />
        </label>
        <label>
          Predmet (Subject ID)
          <input id="f-subj" type="number" min="1" />
        </label>
        <label>
          Početak termina
          <input id="f-start" type="datetime-local" />
        </label>
        <label>
          Kraj termina
          <input id="f-end" type="datetime-local" />
        </label>
      </div>
      <div class="actions-row">
        <button id="forma-btn" type="button" onclick="spremiTermin()">Kreiraj</button>
        <button type="button" class="secondary-button" onclick="zatvoriFormu()">Odustani</button>
      </div>
    </div>

    <div id="admin-termini-lista" class="admin-table-wrapper">
      Klikni "Osvježi" za učitavanje termina.
    </div>
  `;

  ucitajAdminTermine();
}

async function ucitajAdminTermine() {
  const lista = document.querySelector("#admin-termini-lista");
  if (!lista) {
    return;
  }

  lista.innerHTML = "<p class='muted'>Učitavanje...</p>";

  try {
    terminiData = await safeApiFetch("/termini");
    await Promise.all(
      terminiData.map(async (term) => {
        term._occ = await loadOccupancyForTerm(term);
      }),
    );
    renderAdminTabela(lista);
  } catch (error) {
    lista.innerHTML = `<p class="message-error">Greška: ${error.message}</p>`;
  }
}

function renderAdminTabela(container) {
  if (!terminiData.length) {
    container.innerHTML = "<p class='muted'>Nema termina. Kreiraj prvi!</p>";
    return;
  }

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
        ${terminiData.map(renderAdminRow).join("")}
      </tbody>
    </table>
  `;
}

function renderAdminRow(term) {
  const termId = getTermId(term);
  const occupancy = term._occ;
  const capacity = occupancy ? occupancy.capacity : "?";
  const registered = occupancy ? occupancy.registered_students : "?";

  return `
    <tr>
      <td>#${termId}</td>
      <td>${term.professor_id}</td>
      <td>${term.subject_id}</td>
      <td>${fmtDateTime(term.start_time)}</td>
      <td>${fmtDateTime(term.end_time)}</td>
      <td>${registered}/${capacity}</td>
      <td class="table-actions">
        <button type="button" class="secondary-button" onclick="otvoriFormuUredivanje(${termId})">Uredi</button>
        <button type="button" class="danger-button" onclick="obrisiTermin(${termId})">Briši</button>
      </td>
    </tr>
  `;
}

// ── Forma ─────────────────────────────────────────────────────
function otvoriFormuKreiranje() {
  editingTerminId = null;
  document.querySelector("#forma-naslov").textContent = "Novi termin";
  document.querySelector("#forma-btn").textContent = "Kreiraj";
  document.querySelector("#f-prof").value = "";
  document.querySelector("#f-subj").value = "";
  document.querySelector("#f-start").value = "";
  document.querySelector("#f-end").value = "";
  document.querySelector("#termin-forma").style.display = "block";
}

function otvoriFormuUredivanje(id) {
  const term = terminiData.find((item) => Number(getTermId(item)) === Number(id));
  if (!term) {
    return;
  }

  editingTerminId = id;
  document.querySelector("#forma-naslov").textContent = `Uredi termin #${id}`;
  document.querySelector("#forma-btn").textContent = "Spremi izmjene";
  document.querySelector("#f-prof").value = term.professor_id;
  document.querySelector("#f-subj").value = term.subject_id;
  document.querySelector("#f-start").value = term.start_time.slice(0, 16);
  document.querySelector("#f-end").value = term.end_time.slice(0, 16);
  document.querySelector("#termin-forma").style.display = "block";
  document.querySelector("#termin-forma").scrollIntoView({ behavior: "smooth" });
}

function zatvoriFormu() {
  const form = document.querySelector("#termin-forma");
  if (form) {
    form.style.display = "none";
  }
  editingTerminId = null;
}

async function spremiTermin() {
  const professorId = Number.parseInt(document.querySelector("#f-prof").value, 10);
  const subjectId = Number.parseInt(document.querySelector("#f-subj").value, 10);
  const start = document.querySelector("#f-start").value;
  const end = document.querySelector("#f-end").value;

  if (!professorId || !subjectId) {
    prikaziAdminMsg("Profesor i predmet su obavezni.", "error");
    return;
  }

  if (!start || !end) {
    prikaziAdminMsg("Datum i vrijeme su obavezni.", "error");
    return;
  }

  if (new Date(start) >= new Date(end)) {
    prikaziAdminMsg("Početak mora biti prije kraja.", "error");
    return;
  }

  const payload = {
    professor_id: professorId,
    subject_id: subjectId,
    start_time: new Date(start).toISOString(),
    end_time: new Date(end).toISOString(),
  };

  try {
    if (editingTerminId) {
      await safeApiFetch(`/termini/${editingTerminId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      prikaziAdminMsg("Termin uspješno ažuriran!", "ok");
    } else {
      await safeApiFetch("/termini", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      prikaziAdminMsg("Termin uspješno kreiran!", "ok");
    }

    zatvoriFormu();
    await ucitajAdminTermine();
    await ucitajTermine();
  } catch (error) {
    prikaziAdminMsg(`Greška: ${error.message}`, "error");
  }
}

async function obrisiTermin(id) {
  const confirmed = confirm(
    `Obrisati termin #${id}?\n\nSve prijave bit će obrisane. Ova akcija se ne može poništiti.`,
  );

  if (!confirmed) {
    return;
  }

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
  if (!el) {
    return;
  }

  el.textContent = message;
  el.dataset.type = type;
  el.style.display = "block";

  setTimeout(() => {
    el.style.display = "none";
  }, 4000);
}

// Eksplicitno izlažemo funkcije jer se koriste u inline onclick atributima.
window.ucitajTermine = ucitajTermine;
window.prijaviSeNaTermin = prijaviSeNaTermin;
window.odjaviSeSTermina = odjaviSeSTermina;
window.prikaziMojePrijave = prikaziMojePrijave;
window.ucitajAdminTermine = ucitajAdminTermine;
window.otvoriFormuKreiranje = otvoriFormuKreiranje;
window.otvoriFormuUredivanje = otvoriFormuUredivanje;
window.zatvoriFormu = zatvoriFormu;
window.spremiTermin = spremiTermin;
window.obrisiTermin = obrisiTermin;
