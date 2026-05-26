// ============================================================
// termini_admin.js — role-based UI with professor/subject dropdowns
// ============================================================

let terminiData = [];
let mojePrijaveData = [];
let prijavljeniTerminiIds = new Set();
let trenutniKorisnik = null;
let editingTerminId = null;

let profesoriData = [];
let predmetiData = [];
let profesorMap = new Map();
let predmetMap = new Map();

let filterProfesor = "";
let filterPredmet = "";
let filterSamoSlobodni = false;
let filterSamoMoji = false;
let searchQuery = "";

// Kept for static tests and for clear feature traceability.
const FZ14_NOTE = "FZ-14 Admin dropdowns: profesor i predmet se biraju po imenu, ne po ID-u.";

document.addEventListener("DOMContentLoaded", async () => {
    await initApp();
});

async function initApp() {
    if (!isLoggedIn()) {
        renderLoginUI();
        return;
    }

    try {
        trenutniKorisnik = await safeApiFetch("/auth/me");
    } catch {
        trenutniKorisnik = getCurrentTokenUser();
    }

    if (trenutniKorisnik && typeof renderLoggedIn === "function") {
        renderLoggedIn(trenutniKorisnik);
    }

    await loadCatalog();

    const role = normalizeRole(trenutniKorisnik?.role);

    if (role === "admin") {
        renderAdminUI();
    } else if (role === "professor" || role === "profesor") {
        renderProfessorUI();
    } else {
        renderStudentUI();
    }
}

function safeApiFetch(path, options = {}) {
    if (typeof apiFetch !== "function") {
        throw new Error("apiFetch nije učitan.");
    }

    return apiFetch(path, options);
}

function isLoggedIn() {
    return typeof getToken === "function" && Boolean(getToken());
}

function getCurrentTokenUser() {
    if (typeof getToken !== "function" || typeof userFromToken !== "function") {
        return null;
    }

    const token = getToken();
    if (!token) return null;

    return userFromToken(token);
}

function normalizeRole(role) {
    return String(role || "").toLowerCase();
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function fmtDateTime(value) {
    if (!value) return "n/a";

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);

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

function userDisplayName(user) {
    const full = [user?.first_name, user?.last_name].filter(Boolean).join(" ").trim();
    return full || user?.email || "Korisnik";
}

function setMain(html) {
    const main = document.querySelector("main");
    if (!main) return;

    main.innerHTML = html;
}

function renderUserHeader(roleLabel) {
    return `
        <header class="ta-header">
            <div>
                <span class="role-badge ${escapeHtml(normalizeRole(trenutniKorisnik?.role))}">
                    ${escapeHtml(roleLabel)}
                </span>
                <h1>${escapeHtml(userDisplayName(trenutniKorisnik))}</h1>
                <p>${escapeHtml(trenutniKorisnik?.email || "")}</p>
            </div>
            <button class="danger-button" onclick="odjavaKorisnika()">Odjava</button>
        </header>
    `;
}

// ============================================================
// Catalog / dropdown helpers
// ============================================================

async function loadCatalog() {
    try {
        const [professors, subjects] = await Promise.all([
            safeApiFetch("/catalog/professors"),
            safeApiFetch("/catalog/subjects"),
        ]);

        profesoriData = Array.isArray(professors) ? professors : [];
        predmetiData = Array.isArray(subjects) ? subjects : [];
    } catch {
        profesoriData = [];
        predmetiData = [];
    }

    profesorMap = new Map(
        profesoriData.map((professor) => [Number(professor.user_id), professor]),
    );
    predmetMap = new Map(
        predmetiData.map((subject) => [Number(subject.subject_id), subject]),
    );
}

function professorName(professorId) {
    const professor = profesorMap.get(Number(professorId));
    if (!professor) return `Profesor ${professorId}`;

    return userDisplayName(professor);
}

function professorLabel(professor) {
    const name = userDisplayName(professor);
    const email = professor?.email ? ` — ${professor.email}` : "";
    return `${name}${email}`;
}

function subjectName(subjectId) {
    const subject = predmetMap.get(Number(subjectId));
    if (!subject) return `Kolegij ${subjectId}`;

    return subject.name;
}

function renderProfessorOptions(selectedId = "") {
    const selected = String(selectedId || "");

    if (!profesoriData.length) {
        return `<option value="">Nema profesora u katalogu</option>`;
    }

    return [
        `<option value="">Odaberi profesora</option>`,
        ...profesoriData.map((professor) => {
            const id = String(professor.user_id);
            const isSelected = id === selected ? "selected" : "";
            return `<option value="${escapeHtml(id)}" ${isSelected}>${escapeHtml(
                professorLabel(professor),
            )}</option>`;
        }),
    ].join("");
}

function renderSubjectOptions(selectedId = "") {
    const selected = String(selectedId || "");

    if (!predmetiData.length) {
        return `<option value="">Nema kolegija u katalogu</option>`;
    }

    return [
        `<option value="">Odaberi kolegij</option>`,
        ...predmetiData.map((subject) => {
            const id = String(subject.subject_id);
            const isSelected = id === selected ? "selected" : "";
            return `<option value="${escapeHtml(id)}" ${isSelected}>${escapeHtml(
                subject.name,
            )}</option>`;
        }),
    ].join("");
}

// ============================================================
// Login / register
// ============================================================

function renderLoginUI() {
    setMain(`
        <section class="login-screen">
            <div class="login-card">
                <div class="brand-mark">TERMINI</div>
                <h1>Konzultacije i laboratoriji</h1>
                <p>Prijavite se za pristup sustavu.</p>

                <div class="form-grid single">
                    <label>
                        Email
                        <input id="lo-email" type="email" autocomplete="email" placeholder="admin@example.com">
                    </label>
                    <label>
                        Lozinka
                        <input id="lo-pass" type="password" autocomplete="current-password" placeholder="Lozinka">
                    </label>
                </div>

                <div id="login-overlay-msg" class="msg-box" style="display:none"></div>

                <div class="form-actions">
                    <button class="primary-button" onclick="loginOverlay()">Prijavi se</button>
                    <button class="secondary-button" onclick="renderRegisterUI()">Registracija</button>
                </div>

                <div class="demo-box">
                    <strong>Demo:</strong><br>
                    admin@example.com / admin123<br>
                    student1@example.com / test123
                </div>
            </div>
        </section>
    `);

    document.querySelector("#lo-pass")?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") loginOverlay();
    });
}

function renderRegisterUI() {
    setMain(`
        <section class="login-screen">
            <div class="login-card">
                <div class="brand-mark">TERMINI</div>
                <h1>Registracija</h1>
                <p>Nova registracija kreira korisnika s rolom student.</p>

                <div class="form-grid single">
                    <label>Ime<input id="lo-ime" type="text" autocomplete="given-name"></label>
                    <label>Prezime<input id="lo-prezime" type="text" autocomplete="family-name"></label>
                    <label>Email<input id="lo-email" type="email" autocomplete="email"></label>
                    <label>Lozinka<input id="lo-pass" type="password" autocomplete="new-password"></label>
                </div>

                <div id="login-overlay-msg" class="msg-box" style="display:none"></div>

                <div class="form-actions">
                    <button class="primary-button" onclick="registerOverlay()">Registriraj se</button>
                    <button class="secondary-button" onclick="renderLoginUI()">Natrag na prijavu</button>
                </div>
            </div>
        </section>
    `);
}

async function loginOverlay() {
    const email = document.querySelector("#lo-email")?.value?.trim();
    const password = document.querySelector("#lo-pass")?.value;
    const msg = document.querySelector("#login-overlay-msg");

    if (!email || !password) {
        showMessage(msg, "Unesite email i lozinku.", "error");
        return;
    }

    const body = new URLSearchParams();
    body.set("username", email);
    body.set("password", password);

    try {
        const response = await fetch("/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body,
        });

        const data = await response.json().catch(() => null);

        if (!response.ok) {
            throw new Error(data?.detail || "Greška pri prijavi.");
        }

        if (typeof setToken === "function") {
            setToken(data.access_token);
        } else {
            localStorage.setItem("access_token", data.access_token);
        }

        if (typeof loadCurrentUser === "function") {
            trenutniKorisnik = await loadCurrentUser({ keepTokenFallback: true });
        } else if (typeof userFromToken === "function") {
            trenutniKorisnik = userFromToken(data.access_token);
        }

        await initApp();
    } catch (error) {
        showMessage(msg, error.message, "error");
    }
}

async function registerOverlay() {
    const firstName = document.querySelector("#lo-ime")?.value?.trim();
    const lastName = document.querySelector("#lo-prezime")?.value?.trim();
    const email = document.querySelector("#lo-email")?.value?.trim();
    const password = document.querySelector("#lo-pass")?.value;
    const msg = document.querySelector("#login-overlay-msg");

    if (!firstName || !lastName || !email || !password) {
        showMessage(msg, "Sva polja su obavezna.", "error");
        return;
    }

    try {
        const response = await fetch("/auth/register", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                first_name: firstName,
                last_name: lastName,
                email,
                password,
            }),
        });

        const data = await response.json().catch(() => null);

        if (!response.ok) {
            throw new Error(data?.detail || "Greška pri registraciji.");
        }

        showMessage(msg, "Registracija uspješna. Sada se prijavite.", "ok");
        setTimeout(renderLoginUI, 1200);
    } catch (error) {
        showMessage(msg, error.message, "error");
    }
}

function showMessage(el, message, type = "info") {
    if (!el) return;

    el.textContent = message;
    el.dataset.type = type;
    el.style.display = "block";
}

function odjavaKorisnika() {
    if (typeof logoutApp === "function") {
        logoutApp();
        return;
    }

    if (typeof clearToken === "function") {
        clearToken();
    } else {
        localStorage.removeItem("access_token");
    }

    trenutniKorisnik = null;
    terminiData = [];
    mojePrijaveData = [];
    prijavljeniTerminiIds = new Set();

    if (typeof renderLoggedOut === "function") {
        renderLoggedOut();
    }

    renderLoginUI();
}

// ============================================================
// Student UI
// ============================================================

function renderStudentUI() {
    setMain(`
        <section class="ta-shell">
            ${renderUserHeader("Student")}

            <section class="panel my-registrations-box">
                <div class="panel-header">
                    <div>
                        <h2>Moje prijave</h2>
                        <p>Termini na koje ste trenutno prijavljeni.</p>
                    </div>
                    <button class="secondary-button" onclick="osvjeziMojePrijave()">Osvježi</button>
                </div>
                <div id="moje-prijave" class="card-grid">Učitavanje...</div>
            </section>

            <section class="panel">
                <div class="panel-header">
                    <div>
                        <h2>Termini konzultacija</h2>
                        <p>Pregledajte dostupne termine i prijavite se.</p>
                    </div>
                    <button class="secondary-button" onclick="ucitajTermine()">Osvježi</button>
                </div>

                ${renderFilterBar()}

                <div id="terms-msg" class="msg-box" style="display:none"></div>
                <div id="termini-lista" class="card-grid">Učitavanje...</div>
            </section>
        </section>
    `);

    setupFilterListeners();
    ucitajTermine();
    osvjeziMojePrijave();
}

function renderFilterBar() {
    return `
        <div class="filter-bar">
            <input id="search-input" type="search" placeholder="Pretraga po profesoru ili kolegiju">
            <select id="filter-profesor">
                <option value="">Svi profesori</option>
                ${renderProfessorOptions(filterProfesor)}
            </select>
            <select id="filter-predmet">
                <option value="">Svi kolegiji</option>
                ${renderSubjectOptions(filterPredmet)}
            </select>
            <label class="check-row">
                <input id="filter-slobodni" type="checkbox">
                Samo slobodni
            </label>
            <label class="check-row">
                <input id="filter-moji" type="checkbox">
                Samo moji
            </label>
            <button class="secondary-button" onclick="resetFilters()">Reset</button>
        </div>
    `;
}

function setupFilterListeners() {
    const bind = (id, fn) => {
        const el = document.querySelector(`#${id}`);
        if (!el) return;

        el.addEventListener("input", fn);
        el.addEventListener("change", fn);
    };

    bind("search-input", (event) => {
        searchQuery = event.target.value.trim();
        renderFilteredTermini();
    });

    bind("filter-profesor", (event) => {
        filterProfesor = event.target.value.trim();
        renderFilteredTermini();
    });

    bind("filter-predmet", (event) => {
        filterPredmet = event.target.value.trim();
        renderFilteredTermini();
    });

    bind("filter-slobodni", (event) => {
        filterSamoSlobodni = event.target.checked;
        renderFilteredTermini();
    });

    bind("filter-moji", (event) => {
        filterSamoMoji = event.target.checked;
        renderFilteredTermini();
    });
}

function resetFilters() {
    filterProfesor = "";
    filterPredmet = "";
    filterSamoSlobodni = false;
    filterSamoMoji = false;
    searchQuery = "";

    ["search-input", "filter-profesor", "filter-predmet"].forEach((id) => {
        const el = document.querySelector(`#${id}`);
        if (el) el.value = "";
    });

    ["filter-slobodni", "filter-moji"].forEach((id) => {
        const el = document.querySelector(`#${id}`);
        if (el) el.checked = false;
    });

    renderFilteredTermini();
}

// ============================================================
// Professor / admin UI
// ============================================================

function renderProfessorUI() {
    setMain(`
        <section class="ta-shell">
            ${renderUserHeader("Profesor")}

            <section class="panel">
                <div class="panel-header">
                    <div>
                        <h2>Moji termini</h2>
                        <p>Termini koje držite kao profesor.</p>
                    </div>
                    <div class="panel-actions">
                        <button class="secondary-button" onclick="ucitajProfesorTermine()">Osvježi</button>
                        <button class="primary-button" onclick="otvoriFormuKreiranje()">Novi termin</button>
                    </div>
                </div>

                ${renderTerminForm(false)}

                <div id="admin-msg" class="msg-box" style="display:none"></div>
                <div id="admin-termini-lista" class="table-wrap">Učitavanje...</div>
            </section>
        </section>
    `);

    ucitajProfesorTermine();
}

function renderAdminUI() {
    setMain(`
        <section class="ta-shell admin-shell">
            ${renderUserHeader("Admin")}

            <section class="panel">
                <div class="panel-header">
                    <div>
                        <h2>Upravljanje terminima</h2>
                        <p>Kreiranje, uređivanje i brisanje svih termina.</p>
                    </div>
                    <div class="panel-actions">
                        <button class="secondary-button" onclick="ucitajAdminTermine()">Osvježi</button>
                        <button class="primary-button" onclick="otvoriFormuKreiranje()">Novi termin</button>
                    </div>
                </div>

                ${renderTerminForm(true)}

                <div id="admin-msg" class="msg-box" style="display:none"></div>
                <div id="admin-termini-lista" class="table-wrap">Učitavanje...</div>
            </section>

            <section class="panel">
                <div class="panel-header">
                    <div>
                        <h2>Upravljanje korisnicima</h2>
                        <p>Promjena role korisnika: student, professor ili admin.</p>
                    </div>
                    <button class="secondary-button" onclick="ucitajKorisnike()">Osvježi</button>
                </div>

                <div id="users-msg" class="msg-box" style="display:none"></div>
                <div id="admin-korisnici-lista" class="table-wrap">Učitavanje...</div>
            </section>
        </section>
    `);

    ucitajAdminTermine();
    ucitajKorisnike();
}

function renderTerminForm(isAdmin) {
    return `
        <div id="termin-forma" class="form-card" style="display:none">
            <h3 id="forma-naslov">Novi termin</h3>
            <div class="form-grid">
                ${
                    isAdmin
                        ? `<label>Profesor<select id="f-prof">${renderProfessorOptions()}</select></label>`
                        : ""
                }
                <label>Kolegij<select id="f-subj">${renderSubjectOptions()}</select></label>
                <label>Početak<input id="f-start" type="datetime-local"></label>
                <label>Kraj<input id="f-end" type="datetime-local"></label>
            </div>
            <div class="form-actions">
                <button id="forma-btn" class="primary-button" onclick="${
                    isAdmin ? "spremiTermin()" : "spremiProfesorTermin()"
                }">Kreiraj</button>
                <button class="secondary-button" onclick="zatvoriFormu()">Odustani</button>
            </div>
        </div>
    `;
}

// Backward compatible name kept for old static tests.
function renderAdminSection() {
    renderAdminUI();
}

// ============================================================
// Loading terms and occupancy
// ============================================================

async function loadMojePrijaveSilently() {
    try {
        const prijave = await safeApiFetch("/me/prijave");
        normalizeMojePrijave(prijave);
    } catch {
        normalizeMojePrijave([]);
    }
}

function normalizeMojePrijave(prijave) {
    mojePrijaveData = Array.isArray(prijave) ? prijave : [];
    prijavljeniTerminiIds = new Set();

    for (const prijava of mojePrijaveData) {
        const termId = prijava.term_id ?? prijava.termin?.term_id ?? prijava.termin?.id;
        if (termId != null) {
            prijavljeniTerminiIds.add(Number(termId));
        }
    }
}

async function loadOccupancyForTerm(term) {
    const termId = getTermId(term);

    try {
        return await safeApiFetch(`/termini/${termId}/popunjenost`);
    } catch {
        try {
            return await safeApiFetch(`/termini/popunjenost/${termId}`);
        } catch {
            return null;
        }
    }
}

async function ucitajTermine() {
    const lista = document.querySelector("#termini-lista");
    if (!lista) return;

    lista.innerHTML = `<div class="empty-state">Učitavanje termina...</div>`;

    try {
        terminiData = await safeApiFetch("/termini");
        await loadMojePrijaveSilently();
        await Promise.all(
            terminiData.map(async (termin) => {
                termin._occ = await loadOccupancyForTerm(termin);
            }),
        );

        renderFilteredTermini();
        renderMojePrijave();
    } catch (error) {
        lista.innerHTML = `<div class="empty-state error-text">Greška: ${escapeHtml(error.message)}</div>`;
    }
}

function filtrirajTermine(termini) {
    return termini.filter((term) => {
        const termId = Number(getTermId(term));
        const professor = professorName(term.professor_id).toLowerCase();
        const subject = subjectName(term.subject_id).toLowerCase();

        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            const match = professor.includes(q) || subject.includes(q);

            if (!match) return false;
        }

        if (filterProfesor && String(term.professor_id) !== String(filterProfesor)) {
            return false;
        }

        if (filterPredmet && String(term.subject_id) !== String(filterPredmet)) {
            return false;
        }

        if (filterSamoSlobodni && term._occ?.full) {
            return false;
        }

        if (filterSamoMoji && !prijavljeniTerminiIds.has(termId)) {
            return false;
        }

        return true;
    });
}

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

    const fmt = (date) =>
        date.toLocaleDateString("hr-HR", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
        });

    return `Tjedan ${fmt(monday)} — ${fmt(sunday)}`;
}

function groupByWeek(termini) {
    const groups = new Map();
    const sorted = [...termini].sort(
        (a, b) => new Date(a.start_time) - new Date(b.start_time),
    );

    for (const termin of sorted) {
        const key = getWeekKey(termin.start_time);

        if (!groups.has(key)) {
            groups.set(key, []);
        }

        groups.get(key).push(termin);
    }

    return groups;
}

function renderFilteredTermini() {
    const lista = document.querySelector("#termini-lista");
    if (!lista) return;

    const filtered = filtrirajTermine(terminiData);

    if (!filtered.length) {
        lista.innerHTML = `<div class="empty-state">Nema termina koji odgovaraju filterima.</div>`;
        return;
    }

    const groups = groupByWeek(filtered);
    let html = "";

    for (const [weekKey, termini] of groups) {
        html += `
            <section class="week-group">
                <h3>${escapeHtml(getWeekLabel(weekKey))}</h3>
                <div class="card-grid">
                    ${termini.map(renderTerminCard).join("")}
                </div>
            </section>
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
    const percent =
        occ && Number(occ.capacity) > 0
            ? Math.min(100, Math.round((occ.registered_students / occ.capacity) * 100))
            : 0;

    const actionButton = isRegistered
        ? `<button class="danger-button" onclick="odjaviSeSTermina(${termId})">Odjavi se</button>`
        : `<button class="primary-button" ${full ? "disabled" : ""} onclick="prijaviSeNaTermin(${termId})">
                ${full ? "Popunjeno" : "Prijavi se"}
           </button>`;

    return `
        <article class="termin-card ${isRegistered ? "is-registered" : ""} ${full ? "is-full" : ""}">
            <div class="card-top">
                <h3>${escapeHtml(subjectName(term.subject_id))}</h3>
                ${isRegistered ? `<span class="status-pill ok">Prijavljen/a</span>` : ""}
                ${full ? `<span class="status-pill danger">Popunjeno</span>` : ""}
            </div>

            <div class="term-meta">
                <span>Profesor: <strong>${escapeHtml(professorName(term.professor_id))}</strong></span>
                <span>Kolegij: <strong>${escapeHtml(subjectName(term.subject_id))}</strong></span>
            </div>

            <div class="term-time">
                <span>${escapeHtml(fmtDateTime(term.start_time))}</span>
                <span>${escapeHtml(fmtDateTime(term.end_time))}</span>
                <span>${Number.isFinite(minutes) ? minutes : "?"} min</span>
            </div>

            ${renderProgressBar(registered, capacity, percent)}

            <div class="card-actions">
                ${actionButton}
            </div>
        </article>
    `;
}

function renderProgressBar(registered, capacity, percent) {
    return `
        <div class="occupancy-box">
            <div class="occupancy-row">
                <span>Popunjenost</span>
                <strong>${escapeHtml(registered)}/${escapeHtml(capacity)}</strong>
            </div>
            <div class="progress-track">
                <div class="progress-fill" style="width:${escapeHtml(percent)}%"></div>
            </div>
        </div>
    `;
}

// ============================================================
// Student registration actions
// ============================================================

async function prijaviSeNaTermin(termId) {
    const msg = document.querySelector("#terms-msg");

    try {
        await safeApiFetch(`/termini/${termId}/prijava`, {
            method: "POST",
        });

        showMessage(msg, `Prijavljen/a na termin.`, "ok");
        await ucitajTermine();
        await osvjeziMojePrijave();
    } catch (error) {
        showMessage(msg, `Prijava nije uspjela: ${error.message}`, "error");
    }
}

async function odjaviSeSTermina(termId) {
    const msg = document.querySelector("#terms-msg");

    try {
        await safeApiFetch(`/termini/${termId}/prijava`, {
            method: "DELETE",
        });

        showMessage(msg, `Odjavljen/a s termina.`, "ok");
        await ucitajTermine();
        await osvjeziMojePrijave();
    } catch (error) {
        showMessage(msg, `Odjava nije uspjela: ${error.message}`, "error");
    }
}

async function osvjeziMojePrijave() {
    try {
        const prijave = await safeApiFetch("/me/prijave");
        normalizeMojePrijave(prijave);
    } catch {
        normalizeMojePrijave([]);
    }

    renderMojePrijave();
}

function renderMojePrijave() {
    const container = document.querySelector("#moje-prijave");
    if (!container) return;

    if (!mojePrijaveData.length) {
        container.innerHTML = `<div class="empty-state">Trenutno nema aktivnih prijava.</div>`;
        return;
    }

    container.innerHTML = mojePrijaveData
        .map((prijava) => {
            const term = prijava.termin;
            const termId = prijava.term_id ?? term?.term_id ?? "?";

            return `
                <article class="mini-card">
                    <h3>${escapeHtml(subjectName(term?.subject_id))}</h3>
                    <p>${escapeHtml(professorName(term?.professor_id))}</p>
                    <p>${escapeHtml(fmtDateTime(term?.start_time))} — ${escapeHtml(fmtDateTime(term?.end_time))}</p>
                    <button class="danger-button" onclick="odjaviSeSTermina(${Number(termId)})">Odjavi se</button>
                </article>
            `;
        })
        .join("");
}

// ============================================================
// Admin / professor term CRUD
// ============================================================

async function ucitajAdminTermine() {
    const lista = document.querySelector("#admin-termini-lista");
    if (!lista) return;

    lista.innerHTML = `<div class="empty-state">Učitavanje termina...</div>`;

    try {
        terminiData = await safeApiFetch("/termini");
        await Promise.all(
            terminiData.map(async (termin) => {
                termin._occ = await loadOccupancyForTerm(termin);
            }),
        );

        renderAdminTabela(lista);
    } catch (error) {
        lista.innerHTML = `<div class="empty-state error-text">Greška: ${escapeHtml(error.message)}</div>`;
    }
}

async function ucitajProfesorTermine() {
    const lista = document.querySelector("#admin-termini-lista");
    if (!lista) return;

    lista.innerHTML = `<div class="empty-state">Učitavanje termina...</div>`;

    try {
        const sviTermini = await safeApiFetch("/termini");
        const professorId = trenutniKorisnik?.user_id ?? trenutniKorisnik?.id;

        terminiData = sviTermini.filter(
            (termin) => Number(termin.professor_id) === Number(professorId),
        );

        await Promise.all(
            terminiData.map(async (termin) => {
                termin._occ = await loadOccupancyForTerm(termin);
            }),
        );

        renderAdminTabela(lista);
    } catch (error) {
        lista.innerHTML = `<div class="empty-state error-text">Greška: ${escapeHtml(error.message)}</div>`;
    }
}

function renderAdminTabela(container) {
    if (!terminiData.length) {
        container.innerHTML = `<div class="empty-state">Nema termina za prikaz.</div>`;
        return;
    }

    const sorted = [...terminiData].sort(
        (a, b) => new Date(a.start_time) - new Date(b.start_time),
    );

    container.innerHTML = `
        <table class="admin-table">
            <thead>
                <tr>
                    <th>Termin</th>
                    <th>Profesor</th>
                    <th>Kolegij</th>
                    <th>Početak</th>
                    <th>Kraj</th>
                    <th>Popunjenost</th>
                    <th>Akcije</th>
                </tr>
            </thead>
            <tbody>
                ${sorted
                    .map((termin) => {
                        const termId = getTermId(termin);
                        const occ = termin._occ;

                        return `
                            <tr>
                                <td>${escapeHtml(subjectName(termin.subject_id))}</td>
                                <td>${escapeHtml(professorName(termin.professor_id))}</td>
                                <td>${escapeHtml(subjectName(termin.subject_id))}</td>
                                <td>${escapeHtml(fmtDateTime(termin.start_time))}</td>
                                <td>${escapeHtml(fmtDateTime(termin.end_time))}</td>
                                <td>${occ ? `${escapeHtml(occ.registered_students)}/${escapeHtml(occ.capacity)}` : "?"}</td>
                                <td class="action-cell">
                                    <button class="secondary-button small" onclick="otvoriFormuUredivanje(${Number(termId)})">Uredi</button>
                                    <button class="danger-button small" onclick="obrisiTermin(${Number(termId)})">Briši</button>
                                </td>
                            </tr>
                        `;
                    })
                    .join("")}
            </tbody>
        </table>
    `;
}

function otvoriFormuKreiranje() {
    editingTerminId = null;

    document.querySelector("#forma-naslov").textContent = "Novi termin";
    document.querySelector("#forma-btn").textContent = "Kreiraj";

    ["f-prof", "f-subj", "f-start", "f-end"].forEach((id) => {
        const el = document.querySelector(`#${id}`);
        if (el) el.value = "";
    });

    const form = document.querySelector("#termin-forma");
    if (form) {
        form.style.display = "block";
        form.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

function otvoriFormuUredivanje(id) {
    const termin = terminiData.find((item) => Number(getTermId(item)) === Number(id));
    if (!termin) return;

    editingTerminId = id;

    document.querySelector("#forma-naslov").textContent = "Uredi termin";
    document.querySelector("#forma-btn").textContent = "Spremi izmjene";

    const profInput = document.querySelector("#f-prof");
    if (profInput) profInput.value = termin.professor_id;

    const subjectInput = document.querySelector("#f-subj");
    const startInput = document.querySelector("#f-start");
    const endInput = document.querySelector("#f-end");

    if (subjectInput) subjectInput.value = termin.subject_id;
    if (startInput) startInput.value = String(termin.start_time).slice(0, 16);
    if (endInput) endInput.value = String(termin.end_time).slice(0, 16);

    const form = document.querySelector("#termin-forma");
    if (form) {
        form.style.display = "block";
        form.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

function zatvoriFormu() {
    const form = document.querySelector("#termin-forma");
    if (form) form.style.display = "none";

    editingTerminId = null;
}

function readTerminPayload(isAdmin) {
    const subjectId = Number.parseInt(document.querySelector("#f-subj")?.value, 10);
    const start = document.querySelector("#f-start")?.value;
    const end = document.querySelector("#f-end")?.value;
    const professorId = isAdmin
        ? Number.parseInt(document.querySelector("#f-prof")?.value, 10)
        : Number(trenutniKorisnik?.user_id ?? trenutniKorisnik?.id);

    if (!professorId) throw new Error("Profesor je obavezan.");
    if (!subjectId) throw new Error("Kolegij je obavezan.");
    if (!start || !end) throw new Error("Početak i kraj termina su obavezni.");
    if (new Date(start) >= new Date(end)) {
        throw new Error("Početak termina mora biti prije kraja.");
    }

    return {
        professor_id: professorId,
        subject_id: subjectId,
        start_time: new Date(start).toISOString(),
        end_time: new Date(end).toISOString(),
    };
}

async function spremiTermin() {
    const msg = document.querySelector("#admin-msg");

    try {
        const payload = readTerminPayload(true);

        if (editingTerminId) {
            await safeApiFetch(`/termini/${editingTerminId}`, {
                method: "PUT",
                body: JSON.stringify(payload),
            });

            showMessage(msg, "Termin je ažuriran.", "ok");
        } else {
            await safeApiFetch("/termini", {
                method: "POST",
                body: JSON.stringify(payload),
            });

            showMessage(msg, "Termin je kreiran.", "ok");
        }

        zatvoriFormu();
        await ucitajAdminTermine();
    } catch (error) {
        showMessage(msg, `Greška: ${error.message}`, "error");
    }
}

async function spremiProfesorTermin() {
    const msg = document.querySelector("#admin-msg");

    try {
        const payload = readTerminPayload(false);

        if (editingTerminId) {
            await safeApiFetch(`/termini/${editingTerminId}`, {
                method: "PUT",
                body: JSON.stringify(payload),
            });

            showMessage(msg, "Termin je ažuriran.", "ok");
        } else {
            await safeApiFetch("/termini", {
                method: "POST",
                body: JSON.stringify(payload),
            });

            showMessage(msg, "Termin je kreiran.", "ok");
        }

        zatvoriFormu();
        await ucitajProfesorTermine();
    } catch (error) {
        showMessage(msg, `Greška: ${error.message}`, "error");
    }
}

async function obrisiTermin(id) {
    const confirmed = confirm(
        "Obrisati termin? Time će se obrisati i povezane prijave studenata.",
    );

    if (!confirmed) return;

    const msg = document.querySelector("#admin-msg");

    try {
        await safeApiFetch(`/termini/${id}`, {
            method: "DELETE",
        });

        showMessage(msg, "Termin je obrisan.", "ok");

        const role = normalizeRole(trenutniKorisnik?.role);
        if (role === "professor" || role === "profesor") {
            await ucitajProfesorTermine();
        } else {
            await ucitajAdminTermine();
        }
    } catch (error) {
        showMessage(msg, `Greška: ${error.message}`, "error");
    }
}

// ============================================================
// Admin role management UI
// ============================================================

async function ucitajKorisnike() {
    const lista = document.querySelector("#admin-korisnici-lista");
    if (!lista) return;

    lista.innerHTML = `<div class="empty-state">Učitavanje korisnika...</div>`;

    try {
        const korisnici = await safeApiFetch("/auth/users");

        if (!Array.isArray(korisnici) || !korisnici.length) {
            lista.innerHTML = `<div class="empty-state">Nema korisnika za prikaz.</div>`;
            return;
        }

        lista.innerHTML = `
            <table class="admin-table">
                <thead>
                    <tr>
                        <th>Korisnik</th>
                        <th>Email</th>
                        <th>Trenutna rola</th>
                        <th>Nova rola</th>
                        <th>office_id</th>
                        <th>Akcija</th>
                    </tr>
                </thead>
                <tbody>
                    ${korisnici.map(renderKorisnikRow).join("")}
                </tbody>
            </table>
        `;
    } catch (error) {
        lista.innerHTML = `<div class="empty-state error-text">Greška: ${escapeHtml(error.message)}</div>`;
    }
}

function renderKorisnikRow(user) {
    const userId = user.user_id ?? user.id;
    const role = normalizeRole(user.role);
    const officeId = user.office_id ?? "";

    return `
        <tr>
            <td>${escapeHtml(user.first_name)} ${escapeHtml(user.last_name)}</td>
            <td>${escapeHtml(user.email)}</td>
            <td><span class="role-badge ${escapeHtml(role)}">${escapeHtml(role)}</span></td>
            <td>
                <select id="role-select-${escapeHtml(userId)}" onchange="onRoleSelectChange(${Number(userId)})">
                    <option value="student" ${role === "student" ? "selected" : ""}>student</option>
                    <option value="professor" ${role === "professor" ? "selected" : ""}>professor</option>
                    <option value="admin" ${role === "admin" ? "selected" : ""}>admin</option>
                </select>
            </td>
            <td>
                <input
                    id="office-input-${escapeHtml(userId)}"
                    type="number"
                    min="1"
                    value="${escapeHtml(officeId)}"
                    placeholder="office_id"
                    ${role === "professor" ? "" : "disabled"}
                >
            </td>
            <td>
                <button class="primary-button small" onclick="spremiKorisnickuRolu(${Number(userId)})">
                    Spremi rolu
                </button>
            </td>
        </tr>
    `;
}

function onRoleSelectChange(userId) {
    const select = document.querySelector(`#role-select-${userId}`);
    const officeInput = document.querySelector(`#office-input-${userId}`);
    if (!select || !officeInput) return;

    const role = normalizeRole(select.value);

    officeInput.disabled = role !== "professor";

    if (role !== "professor") {
        officeInput.value = "";
    }
}

async function spremiKorisnickuRolu(userId) {
    const select = document.querySelector(`#role-select-${userId}`);
    const officeInput = document.querySelector(`#office-input-${userId}`);
    const msg = document.querySelector("#users-msg") || document.querySelector("#admin-msg");

    if (!select) return;

    const role = normalizeRole(select.value);
    const payload = {
        role,
    };

    if (role === "professor") {
        const officeId = Number.parseInt(officeInput?.value, 10);

        if (!officeId) {
            showMessage(msg, "Za rolu professor treba unijeti office_id.", "error");
            return;
        }

        payload.office_id = officeId;
    }

    try {
        await safeApiFetch(`/auth/users/${userId}/role`, {
            method: "PATCH",
            body: JSON.stringify(payload),
        });

        showMessage(msg, `Rola korisnika je ažurirana.`, "ok");
        await loadCatalog();
        await ucitajKorisnike();
    } catch (error) {
        showMessage(msg, `Promjena role nije uspjela: ${error.message}`, "error");
    }
}

// ============================================================
// Public globals used by inline handlers and older tests
// ============================================================

window.initApp = initApp;
window.registerOverlay = registerOverlay;
window.renderRegisterUI = renderRegisterUI;
window.renderLoginUI = renderLoginUI;
window.prikaziRegisterOverlay = renderRegisterUI;
window.prikaziLoginScreen = renderLoginUI;
window.loginOverlay = loginOverlay;
window.odjavaKorisnika = odjavaKorisnika;

window.loadCatalog = loadCatalog;
window.ucitajTermine = ucitajTermine;
window.prijaviSeNaTermin = prijaviSeNaTermin;
window.odjaviSeSTermina = odjaviSeSTermina;
window.osvjeziMojePrijave = osvjeziMojePrijave;
window.resetFilters = resetFilters;

window.renderAdminUI = renderAdminUI;
window.renderAdminSection = renderAdminSection;
window.ucitajAdminTermine = ucitajAdminTermine;
window.ucitajProfesorTermine = ucitajProfesorTermine;
window.otvoriFormuKreiranje = otvoriFormuKreiranje;
window.otvoriFormuUredivanje = otvoriFormuUredivanje;
window.zatvoriFormu = zatvoriFormu;
window.spremiTermin = spremiTermin;
window.spremiProfesorTermin = spremiProfesorTermin;
window.obrisiTermin = obrisiTermin;

window.ucitajKorisnike = ucitajKorisnike;
window.onRoleSelectChange = onRoleSelectChange;
window.spremiKorisnickuRolu = spremiKorisnickuRolu;
