// ============================================================
// Zajednički helperi
// ============================================================

const TOKEN_STORAGE_KEY = "access_token";
const navbarCurrentUser = document.querySelector("#navbar-current-user");

function getToken() { return localStorage.getItem(TOKEN_STORAGE_KEY); }
function setToken(token) { localStorage.setItem(TOKEN_STORAGE_KEY, token); }
function clearToken() { localStorage.removeItem(TOKEN_STORAGE_KEY); }

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(data?.detail || data?.message || "API greška");
    error.status = response.status;
    throw error;
  }
  return data;
}

async function apiFormFetch(path, formBody) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formBody,
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(data?.detail || data?.message || "API greška");
    error.status = response.status;
    throw error;
  }
  return data;
}

function formatDateTime(iso) {
  if (!iso) return "?";
  return new Date(iso).toLocaleString("hr-HR", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function setMessage(elId, message, type = "info") {
  const el = document.querySelector(`#${elId}`);
  if (!el) return;
  el.textContent = message;
  el.dataset.type = type;
}

function clearMessage(elId) {
  const el = document.querySelector(`#${elId}`);
  if (!el) return;
  el.textContent = "";
  delete el.dataset.type;
}

function setButtonLoading(btn, loading, text) {
  if (!btn) return;
  if (loading) {
    btn.dataset.orig = btn.textContent;
    btn.textContent = text;
    btn.disabled = true;
  } else {
    btn.textContent = btn.dataset.orig || btn.textContent;
    btn.disabled = false;
    delete btn.dataset.orig;
  }
}

function validateFormField(form, name, label) {
  const value = new FormData(form).get(name)?.toString().trim() || "";
  if (!value) throw new Error(`${label} je obavezan.`);
  return value;
}

// ============================================================
// JWT / korisnik
// ============================================================

function parseJwtPayload(token) {
  try {
    const [, part] = token.split(".");
    return JSON.parse(atob(part.replace(/-/g, "+").replace(/_/g, "/")));
  } catch { return null; }
}

function userFromToken(token) {
  const p = parseJwtPayload(token);
  if (!p) return null;
  return {
    user_id: p.user_id ?? null,
    first_name: p.first_name ?? "",
    last_name: p.last_name ?? "",
    email: p.sub ?? p.email ?? "",
    role: p.role ?? "student",
    office_id: p.office_id ?? null,
    source: "token",
  };
}

function getUserDisplayName(user) {
  const full = [user.first_name, user.last_name].filter(Boolean).join(" ").trim();
  return full || user.email || "Korisnik";
}

function isAdmin(user) {
  return user?.role === "admin";
}

function isProfessor(user) {
  return user?.role === "professor" || user?.role === "profesor";
}

// ============================================================
// UI – renderiranje korisnika i role
// ============================================================

function renderRoleBadge(user) {
  const badge = document.querySelector("#navbar-role-badge");
  if (!badge) return;
  const role = user?.role ?? "";
  const labels = { admin: "Admin", professor: "Profesor", profesor: "Profesor", student: "Student" };
  badge.textContent = labels[role] ?? role;
  badge.className = `role-badge ${role}`;
  badge.style.display = role ? "inline-block" : "none";
}

function renderLoggedIn(user) {
  const name = getUserDisplayName(user);
  if (navbarCurrentUser) {
    navbarCurrentUser.textContent = name;
    navbarCurrentUser.classList.add("logged-in");
  }
  renderRoleBadge(user);

  const logoutBtn = document.querySelector("#logout-button");
  if (logoutBtn) logoutBtn.style.display = "inline-block";

  const userPanel = document.querySelector("#current-user-panel");
  if (userPanel) userPanel.style.display = "block";

  const box = document.querySelector("#current-user");
  if (box) {
    box.className = "status-box logged-in";
    box.textContent = [
      `Ime: ${getUserDisplayName(user)}`,
      `Email: ${user.email}`,
      `Rola: ${user.role}`,
      `ID: ${user.user_id ?? "n/a"}`,
    ].join("\n");
  }

  // Pokaži admin panel samo adminu
  const adminSection = document.querySelector("#admin");
  if (adminSection) adminSection.style.display = isAdmin(user) ? "block" : "none";
}

function renderLoggedOut() {
  if (navbarCurrentUser) {
    navbarCurrentUser.textContent = "Niste prijavljeni";
    navbarCurrentUser.classList.remove("logged-in");
  }

  const badge = document.querySelector("#navbar-role-badge");
  if (badge) badge.style.display = "none";

  const logoutBtn = document.querySelector("#logout-button");
  if (logoutBtn) logoutBtn.style.display = "none";

  const userPanel = document.querySelector("#current-user-panel");
  if (userPanel) userPanel.style.display = "none";

  const adminSection = document.querySelector("#admin");
  if (adminSection) adminSection.style.display = "none";
}

async function loadCurrentUser(opts = {}) {
  const token = getToken();
  if (!token) { renderLoggedOut(); return null; }

  const tokenUser = userFromToken(token);
  if (tokenUser) renderLoggedIn(tokenUser);

  try {
    const user = await apiFetch("/auth/me");
    renderLoggedIn(user);
    return user;
  } catch (err) {
    if (opts.keepTokenFallback && tokenUser && err.status !== 401) return tokenUser;
    clearToken();
    renderLoggedOut();
    return null;
  }
}

// ============================================================
// Health check
// ============================================================

document.querySelector("#health-button")?.addEventListener("click", async () => {
  const bar = document.querySelector("#health-bar");
  const pre = document.querySelector("#health-result");
  if (!bar || !pre) return;
  const visible = bar.style.display !== "none";
  if (visible) { bar.style.display = "none"; return; }
  pre.textContent = "Učitavanje…";
  bar.style.display = "block";
  try {
    const data = await apiFetch("/health");
    pre.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    pre.textContent = `Greška: ${err.message}`;
  }
});

// ============================================================
// Register
// ============================================================

document.querySelector("#register-submit")?.addEventListener("click", async (event) => {
  event.preventDefault();
  const form = document.querySelector("#register-form");
  const btn = document.querySelector("#register-submit");
  clearMessage("register-message");
  try {
    const first_name = validateFormField(form, "first_name", "Ime");
    const last_name = validateFormField(form, "last_name", "Prezime");
    const email = validateFormField(form, "email", "Email").toLowerCase();
    const password = validateFormField(form, "password", "Lozinka");
    setButtonLoading(btn, true, "Registriram…");
    const user = await apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify({ first_name, last_name, email, password }),
    });
    form.reset();
    setMessage("register-message", `✔ Registrirani ste kao ${user.email}. Sada se prijavite.`, "ok");
  } catch (err) {
    setMessage("register-message", `✖ ${err.message}`, "error");
  } finally {
    setButtonLoading(btn, false);
  }
});

// ============================================================
// Login
// ============================================================

document.querySelector("#login-submit")?.addEventListener("click", async (event) => {
  event.preventDefault();
  const form = document.querySelector("#login-form");
  const btn = document.querySelector("#login-submit");
  clearMessage("auth-message");
  try {
    const email = validateFormField(form, "email", "Email").toLowerCase();
    const password = validateFormField(form, "password", "Lozinka");
    const body = new URLSearchParams();
    body.set("username", email);
    body.set("password", password);
    setButtonLoading(btn, true, "Prijavljivanje…");
    const data = await apiFormFetch("/auth/login", body);
    setToken(data.access_token);
    form.reset();
    const user = userFromToken(data.access_token);
    if (user) renderLoggedIn(user);
    setMessage("auth-message", "✔ Prijava uspješna.", "ok");
    await loadCurrentUser({ keepTokenFallback: true });
    await ucitajTermine();
    await ucitajMojePrijave();
  } catch (err) {
    setMessage("auth-message", `✖ ${err.message}`, "error");
  } finally {
    setButtonLoading(btn, false);
  }
});

// ============================================================
// Logout
// ============================================================

document.querySelector("#logout-button")?.addEventListener("click", () => {
  clearToken();
  renderLoggedOut();
  document.querySelector("#termini-lista").innerHTML = "";
  document.querySelector("#termini-empty").style.display = "none";
  document.querySelector("#prijave-lista").innerHTML = "";
  document.querySelector("#prijave-empty").style.display = "none";
});

// ============================================================
// Osoba 4 – Termini s prijavom/odjavom i progress barom
// ============================================================

function renderProgressBar(registrirani, kapacitet) {
  const pct = kapacitet > 0 ? Math.min(100, Math.round((registrirani / kapacitet) * 100)) : 0;
  const cls = pct >= 100 ? "full" : pct >= 75 ? "warn" : "";
  const badgeCls = pct >= 100 ? "full" : pct >= 75 ? "warn" : "";
  const badgeText = pct >= 100 ? "🔴 POPUNJENO" : `${registrirani}/${kapacitet} mjesta`;
  return `
    <div class="progress-wrap">
      <div class="progress-label">
        <span>Popunjenost</span>
        <span class="capacity-badge ${badgeCls}">${badgeText}</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill ${cls}" style="width:${pct}%"></div>
      </div>
    </div>`;
}

async function ucitajTermine() {
  const lista = document.querySelector("#termini-lista");
  const emptyEl = document.querySelector("#termini-empty");
  if (!lista) return;

  lista.innerHTML = "<p class='muted'>Učitavanje termina…</p>";
  if (emptyEl) emptyEl.style.display = "none";

  try {
    const termini = await apiFetch("/termini");

    if (!termini.length) {
      lista.innerHTML = "";
      if (emptyEl) emptyEl.style.display = "block";
      return;
    }

    let mojaPrijavaIds = new Set();
    try {
      const moje = await apiFetch("/me/prijave");
      mojaPrijavaIds = new Set(moje.map((p) => p.termin?.term_id));
    } catch (_) {}

    lista.innerHTML = "";

    for (const termin of termini) {
      const prijavljen = mojaPrijavaIds.has(termin.term_id);

      let progressHTML = "";
      let popunjen = false;
      try {
        const pop = await apiFetch(`/termini/${termin.term_id}/popunjenost`);
        popunjen = pop.full;
        progressHTML = renderProgressBar(pop.registered_students, pop.capacity);
      } catch (_) {
        progressHTML = `<p class="muted" style="font-size:0.8125rem">Kapacitet nije dostupan</p>`;
      }

      const card = document.createElement("div");
      card.className = `termin-card${popunjen ? " full" : ""}`;
      card.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;flex-wrap:wrap;">
          <strong>Termin #${termin.term_id}</strong>
          ${prijavljen ? '<span class="capacity-badge" style="background:#dcfce7;color:#16a34a">✔ Prijavljen</span>' : ""}
        </div>
        <p class="termin-meta">👤 Profesor ID: ${termin.professor_id} &nbsp;|&nbsp; 📚 Predmet ID: ${termin.subject_id}</p>
        <p class="termin-meta">🕐 ${formatDateTime(termin.start_time)} – ${formatDateTime(termin.end_time)}</p>
        ${progressHTML}
        <div class="termin-actions">
          <button
            class="prijava-btn btn-${prijavljen ? "danger" : "primary"}"
            data-id="${termin.term_id}"
            data-prijavljen="${prijavljen}"
            ${!prijavljen && popunjen ? "disabled title='Termin je popunjen'" : ""}
          >${prijavljen ? "❌ Odjavi se" : "✔ Prijavi se"}</button>
          <span class="prijava-status"></span>
        </div>`;
      lista.appendChild(card);
    }

    lista.querySelectorAll(".prijava-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const termId = Number(btn.dataset.id);
        const prijavljen = btn.dataset.prijavljen === "true";
        const statusEl = btn.nextElementSibling;
        setButtonLoading(btn, true, "…");
        statusEl.textContent = "";
        statusEl.className = "prijava-status";
        try {
          if (prijavljen) {
            await apiFetch(`/termini/${termId}/prijava`, { method: "DELETE" });
            statusEl.textContent = "✔ Odjavljeni ste.";
          } else {
            await apiFetch(`/termini/${termId}/prijava`, { method: "POST" });
            statusEl.textContent = "✔ Prijavljeni ste!";
          }
          setButtonLoading(btn, false);
          await ucitajTermine();
          await ucitajMojePrijave();
        } catch (err) {
          statusEl.textContent = `✖ ${err.message}`;
          statusEl.className = "prijava-status error";
          setButtonLoading(btn, false);
        }
      });
    });
  } catch (err) {
    lista.innerHTML = `<div class="empty-state"><span class="empty-icon">⚠️</span><p>${err.message}</p></div>`;
  }
}

// ============================================================
// Osoba 4 – Moje prijave
// ============================================================

async function ucitajMojePrijave() {
  const lista = document.querySelector("#prijave-lista");
  const emptyEl = document.querySelector("#prijave-empty");
  if (!lista) return;

  lista.innerHTML = "<p class='muted'>Učitavanje…</p>";
  if (emptyEl) emptyEl.style.display = "none";

  try {
    const prijave = await apiFetch("/me/prijave");

    if (!prijave.length) {
      lista.innerHTML = "";
      if (emptyEl) emptyEl.style.display = "block";
      return;
    }

    lista.innerHTML = "";
    prijave.forEach((p) => {
      const t = p.termin;
      const row = document.createElement("div");
      row.className = "prijava-row";
      row.innerHTML = t
        ? `<div>
            <strong>Termin #${t.term_id}</strong>
            <p class="termin-meta">🕐 ${formatDateTime(t.start_time)} – ${formatDateTime(t.end_time)}</p>
            <p class="termin-meta">Prijavljen: ${formatDateTime(p.registered_at)}</p>
           </div>
           <button class="btn-danger odjava-btn" data-id="${t.term_id}">Odjavi se</button>`
        : `<span class="muted">Termin je obrisan (ID: ${p.registration_id})</span>`;
      lista.appendChild(row);
    });

    lista.querySelectorAll(".odjava-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const termId = Number(btn.dataset.id);
        setButtonLoading(btn, true, "…");
        try {
          await apiFetch(`/termini/${termId}/prijava`, { method: "DELETE" });
          await ucitajMojePrijave();
          await ucitajTermine();
        } catch (err) {
          btn.textContent = `✖ ${err.message}`;
          btn.disabled = false;
        }
      });
    });
  } catch (err) {
    lista.innerHTML = `<div class="empty-state"><span class="empty-icon">⚠️</span><p>${err.message}</p></div>`;
  }
}

// ============================================================
// Event listeneri
// ============================================================

document.querySelector("#load-terms-button")?.addEventListener("click", ucitajTermine);
document.querySelector("#load-prijave-btn")?.addEventListener("click", ucitajMojePrijave);

// ============================================================
// Init
// ============================================================

loadCurrentUser().then((user) => {
  if (user) {
    ucitajTermine();
    ucitajMojePrijave();
  }
});

window.appApi = { apiFetch, getToken, setToken, clearToken, ucitajTermine, ucitajMojePrijave };
