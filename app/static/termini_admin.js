// ═══════════════════════════════════════════════════════════
// termini_admin.js — Osoba 3: Admin UI za termine
// Koristi apiFetch() iz script.js (Petar L, Osoba 1)
// ═══════════════════════════════════════════════════════════

// ── Stanje ──────────────────────────────────────────────────
let terminiData = [];
let editingTerminId = null;

// ── Init ────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  renderTerminiSection();
  renderAdminSection();
});

// ── Termini sekcija (vidljiva svima) ────────────────────────
function renderTerminiSection() {
  const section = document.querySelector("#terms");
  if (!section) return;

  section.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Termini</h2>
        <p class="muted">Pregled dostupnih termina konzultacija i laboratorija.</p>
      </div>
      <button id="load-terms-button" type="button" class="secondary-button"
              onclick="ucitajTermine()">
        Učitaj termine
      </button>
    </div>
    <div id="termini-lista">
      <p class="muted">Klikni gumb za učitavanje termina.</p>
    </div>
  `;
}

async function ucitajTermine() {
  const lista = document.querySelector("#termini-lista");
  if (!lista) return;

  lista.innerHTML = "<p class='muted'>Učitavanje...</p>";

  try {
    terminiData = await apiFetch("/termini");

    // Dohvati popunjenost za svaki termin
    await Promise.all(terminiData.map(async (t) => {
      try {
        t._occ = await apiFetch(`/termini/popunjenost/${t.term_id}`);
      } catch {
        t._occ = null;
      }
    }));

    renderTerminiLista(lista);
  } catch (err) {
    lista.innerHTML = `<p style="color:red">Greška: ${err.message}</p>`;
  }
}

function renderTerminiLista(container) {
  if (!terminiData.length) {
    container.innerHTML = "<p class='muted'>Nema dostupnih termina.</p>";
    return;
  }

  const fmt = (iso) =>
    new Date(iso).toLocaleString("hr-HR", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });

  container.innerHTML = `
    <table class="termini-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Početak</th>
          <th>Kraj</th>
          <th>Trajanje</th>
          <th>Popunjenost</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        ${terminiData.map((t) => {
          const start = new Date(t.start_time);
          const end   = new Date(t.end_time);
          const mins  = Math.round((end - start) / 60000);
          const occ   = t._occ;
          const cap   = occ ? occ.capacity   : "?";
          const reg   = occ ? occ.registered_students : "?";
          const pct   = occ && occ.capacity > 0
            ? Math.round((occ.registered_students / occ.capacity) * 100)
            : 0;

          let statusClass, statusText;
          if (!occ || occ.capacity === 0) {
            statusClass = "status-unknown"; statusText = "Nepoznato";
          } else if (occ.full) {
            statusClass = "status-puno"; statusText = "Popunjeno";
          } else if (pct >= 70) {
            statusClass = "status-skoro"; statusText = "Skoro puno";
          } else {
            statusClass = "status-slobodno"; statusText = "Slobodno";
          }

          return `
            <tr>
              <td>#${t.term_id}</td>
              <td>${fmt(start)}</td>
              <td>${fmt(end)}</td>
              <td>${mins} min</td>
              <td>
                <div class="occ-wrap">
                  <div class="occ-bar">
                    <div class="occ-fill occ-${pct >= 100 ? "red" : pct >= 70 ? "yellow" : "green"}"
                         style="width:${Math.min(pct, 100)}%"></div>
                  </div>
                  <span>${reg}/${cap}</span>
                </div>
              </td>
              <td><span class="status-badge ${statusClass}">${statusText}</span></td>
            </tr>`;
        }).join("")}
      </tbody>
    </table>
  `;
}

// ── Admin sekcija (samo admin) ───────────────────────────────
function renderAdminSection() {
  const section = document.querySelector("#admin");
  if (!section) return;

  section.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Admin — Upravljanje terminima</h2>
        <p class="muted">Kreiranje, uređivanje i brisanje termina. Dostupno samo adminima.</p>
      </div>
      <div style="display:flex;gap:8px">
        <button type="button" class="secondary-button" onclick="ucitajAdminTermine()">
          Osvježi
        </button>
        <button type="button" id="btn-novi-termin" onclick="otvoriFormuKreiranje()">
          + Novi termin
        </button>
      </div>
    </div>

    <div id="admin-msg" class="message-box" role="status" style="display:none"></div>

    <!-- Forma za kreiranje/uređivanje -->
    <div id="termin-forma" class="card" style="display:none;margin-bottom:16px">
      <h3 id="forma-naslov">Novi termin</h3>
      <div class="form-stack">
        <label for="f-prof">Profesor (User ID)</label>
        <input type="number" id="f-prof" placeholder="npr. 2" min="1"/>

        <label for="f-subj">Predmet (Subject ID)</label>
        <input type="number" id="f-subj" placeholder="npr. 1" min="1"/>

        <label for="f-start">Početak termina</label>
        <input type="datetime-local" id="f-start"/>

        <label for="f-end">Kraj termina</label>
        <input type="datetime-local" id="f-end"/>

        <div style="display:flex;gap:8px;margin-top:8px">
          <button type="button" id="forma-btn" onclick="spremiTermin()">Kreiraj</button>
          <button type="button" class="secondary-button" onclick="zatvoriFormu()">Odustani</button>
        </div>
      </div>
    </div>

    <!-- Tablica termina -->
    <div id="admin-termini-lista">
      <p class="muted">Klikni "Osvježi" za učitavanje termina.</p>
    </div>
  `;

  // Provjeri je li korisnik admin
  const token = getToken();
  if (token) {
    const user = userFromToken(token);
    if (user && user.role !== "ADMIN") {
      section.innerHTML = `
        <h2>Admin — Upravljanje terminima</h2>
        <p class="muted">Ova sekcija je dostupna samo administratorima.</p>
      `;
    } else {
      ucitajAdminTermine();
    }
  }
}

async function ucitajAdminTermine() {
  const lista = document.querySelector("#admin-termini-lista");
  if (!lista) return;

  lista.innerHTML = "<p class='muted'>Učitavanje...</p>";

  try {
    terminiData = await apiFetch("/termini");
    await Promise.all(terminiData.map(async (t) => {
      try { t._occ = await apiFetch(`/termini/popunjenost/${t.term_id}`); }
      catch { t._occ = null; }
    }));
    renderAdminTabela(lista);
  } catch (err) {
    lista.innerHTML = `<p style="color:red">Greška: ${err.message}</p>`;
  }
}

function renderAdminTabela(container) {
  if (!terminiData.length) {
    container.innerHTML = "<p class='muted'>Nema termina. Kreiraj prvi!</p>";
    return;
  }

  const fmt = (iso) =>
    new Date(iso).toLocaleString("hr-HR", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });

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
        ${terminiData.map((t) => {
          const occ = t._occ;
          const cap = occ ? occ.capacity : "?";
          const reg = occ ? occ.registered_students : "?";

          return `
            <tr>
              <td>#${t.term_id}</td>
              <td>${t.professor_id}</td>
              <td>${t.subject_id}</td>
              <td>${fmt(new Date(t.start_time))}</td>
              <td>${fmt(new Date(t.end_time))}</td>
              <td>${reg}/${cap}</td>
              <td>
                <button type="button" class="secondary-button"
                        onclick="otvoriFormuUredivanje(${t.term_id})"
                        style="margin-right:4px">Uredi</button>
                <button type="button"
                        onclick="obrisiTermin(${t.term_id})"
                        style="background:#dc3545;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer">
                  Briši
                </button>
              </td>
            </tr>`;
        }).join("")}
      </tbody>
    </table>
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
  const t = terminiData.find((x) => x.term_id === id);
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
  const prof  = parseInt(document.querySelector("#f-prof").value);
  const subj  = parseInt(document.querySelector("#f-subj").value);
  const start = document.querySelector("#f-start").value;
  const end   = document.querySelector("#f-end").value;

  if (!prof || !subj) { prikaziAdminMsg("Profesor i predmet su obavezni.", "error"); return; }
  if (!start || !end)  { prikaziAdminMsg("Datum i vrijeme su obavezni.", "error"); return; }
  if (new Date(start) >= new Date(end)) {
    prikaziAdminMsg("Početak mora biti prije kraja.", "error"); return;
  }

  const payload = {
    professor_id: prof,
    subject_id:   subj,
    start_time:   new Date(start).toISOString(),
    end_time:     new Date(end).toISOString(),
  };

  try {
    if (editingTerminId) {
      await apiFetch(`/termini/${editingTerminId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      prikaziAdminMsg("Termin uspješno ažuriran!", "ok");
    } else {
      await apiFetch("/termini", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      prikaziAdminMsg("Termin uspješno kreiran!", "ok");
    }
    zatvoriFormu();
    ucitajAdminTermine();
    ucitajTermine(); // osvježi i javnu listu
  } catch (err) {
    prikaziAdminMsg(`Greška: ${err.message}`, "error");
  }
}

async function obrisiTermin(id) {
  if (!confirm(`Obrisati termin #${id}?\n\nSve prijave bit će obrisane. Ova akcija se ne može poništiti.`)) return;

  try {
    await apiFetch(`/termini/${id}`, { method: "DELETE" });
    prikaziAdminMsg(`Termin #${id} obrisan.`, "ok");
    ucitajAdminTermine();
    ucitajTermine();
  } catch (err) {
    prikaziAdminMsg(`Greška: ${err.message}`, "error");
  }
}

function prikaziAdminMsg(msg, type) {
  const el = document.querySelector("#admin-msg");
  if (!el) return;
  el.textContent = msg;
  el.dataset.type = type;
  el.style.display = "block";
  setTimeout(() => { el.style.display = "none"; }, 4000);
}
