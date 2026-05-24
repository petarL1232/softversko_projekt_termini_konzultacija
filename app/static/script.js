// Minimalni frontend helperi.
// TODO osoba 1: login/register treba spremati token pomocu setToken(token).
// TODO osoba 3: admin UI treba koristiti apiFetch("/termini", ...).
// TODO osoba 4: prijava/odjava treba koristiti apiFetch("/termini/{id}/prijava", ...).

const TOKEN_STORAGE_KEY = "access_token";

const healthButton = document.querySelector("#health-button");
const refreshUserButton = document.querySelector("#refresh-user-button");
const healthResult = document.querySelector("#health-result");
const registerForm = document.querySelector("#register-form");
const registerSubmitButton = document.querySelector("#register-submit");
const loginForm = document.querySelector("#login-form");
const loginSubmitButton = document.querySelector("#login-submit");
const logoutButton = document.querySelector("#logout-button");
const currentUserBox = document.querySelector("#current-user");
const authMessage = document.querySelector("#auth-message");
const loadTermsButton = document.querySelector("#load-terms-button");
const termsResult = document.querySelector("#terms-result");
const navbarCurrentUser = document.querySelector("#navbar-current-user");
const scriptStatus = document.querySelector("#script-status");

function getToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

function setMessage(message, type = "info") {
  if (!authMessage) {
    return;
  }

  authMessage.textContent = message;
  authMessage.dataset.type = type;
}

function clearMessage() {
  if (!authMessage) {
    return;
  }

  authMessage.textContent = "";
  delete authMessage.dataset.type;
}

function setButtonLoading(button, isLoading, loadingText) {
  if (!button) {
    return;
  }

  if (isLoading) {
    button.dataset.originalText = button.textContent || "";
    button.textContent = loadingText;
    button.disabled = true;
    return;
  }

  button.textContent = button.dataset.originalText || button.textContent;
  button.disabled = false;
  delete button.dataset.originalText;
}

function parseJwtPayload(token) {
  try {
    const [, payloadPart] = token.split(".");
    const normalizedPayload = payloadPart.replace(/-/g, "+").replace(/_/g, "/");
    const decodedPayload = atob(normalizedPayload);
    const jsonPayload = decodeURIComponent(
      decodedPayload
        .split("")
        .map((character) => {
          const hex = character.charCodeAt(0).toString(16).padStart(2, "0");
          return `%${hex}`;
        })
        .join(""),
    );

    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

function userFromToken(token) {
  const payload = parseJwtPayload(token);

  if (!payload) {
    return null;
  }

  return {
    user_id: payload.user_id ?? null,
    first_name: payload.first_name ?? "",
    last_name: payload.last_name ?? "",
    email: payload.sub ?? payload.email ?? "nepoznat-email",
    role: payload.role ?? "unknown",
    office_id: payload.office_id ?? null,
    source: "token",
  };
}

function getUserDisplayName(user) {
  const fullName = [user.first_name, user.last_name]
    .filter(Boolean)
    .map((part) => part.trim())
    .filter(Boolean)
    .join(" ");

  return fullName || user.email || "Nepoznati korisnik";
}

function formatUser(user) {
  const id = user.user_id ?? user.id;
  const displayName = getUserDisplayName(user);
  const sourceMessage = user.source === "token" ? "Podaci privremeno procitani iz JWT tokena." : "Podaci procitani preko GET /auth/me.";

  return [
    `ID: ${id ?? "n/a"}`,
    `Ime: ${displayName}`,
    `Email: ${user.email ?? "n/a"}`,
    `Rola: ${user.role ?? "n/a"}`,
    `Office ID: ${user.office_id ?? "n/a"}`,
    sourceMessage,
  ].join("\n");
}

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(path, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message = data?.detail || data?.message || "API greska";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return data;
}

async function apiFormFetch(path, formBody) {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formBody,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message = data?.detail || data?.message || "API greska";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return data;
}

async function testHealth() {
  if (!healthResult) {
    return;
  }

  healthResult.textContent = "Ucitavanje...";

  try {
    const data = await apiFetch("/health");
    healthResult.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    healthResult.textContent = `Greska: ${error.message}`;
  }
}

function validateFormField(form, fieldName, label) {
  const value = new FormData(form).get(fieldName)?.toString().trim() || "";

  if (!value) {
    throw new Error(`${label} je obavezan.`);
  }

  return value;
}

async function registerUser(event) {
  event?.preventDefault();
  clearMessage();

  try {
    const firstName = validateFormField(registerForm, "first_name", "Ime");
    const lastName = validateFormField(registerForm, "last_name", "Prezime");
    const email = validateFormField(registerForm, "email", "Email").toLowerCase();
    const password = validateFormField(registerForm, "password", "Lozinka");

    const payload = {
      first_name: firstName,
      last_name: lastName,
      email,
      password,
    };

    setButtonLoading(registerSubmitButton, true, "Registriram...");

    const user = await apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    registerForm.reset();
    setMessage(`Registracija uspjela za ${user.email}. Sada se loginaj.`, "ok");
  } catch (error) {
    setMessage(`Registracija nije uspjela: ${error.message}`, "error");
  } finally {
    setButtonLoading(registerSubmitButton, false);
  }
}

async function loginUser(event) {
  event?.preventDefault();
  clearMessage();

  try {
    const email = validateFormField(loginForm, "email", "Email").toLowerCase();
    const password = validateFormField(loginForm, "password", "Lozinka");
    const body = new URLSearchParams();

    body.set("username", email);
    body.set("password", password);

    setButtonLoading(loginSubmitButton, true, "Logiram...");

    const data = await apiFormFetch("/auth/login", body);
    setToken(data.access_token);
    loginForm.reset();

    const tokenUser = userFromToken(data.access_token);
    if (tokenUser) {
      renderLoggedIn(tokenUser);
    }

    setMessage("Login uspjesan. Token je spremljen u localStorage.", "ok");
    await loadCurrentUser({ keepTokenFallback: true });

    // Osoba 4: učitaj termine i prijave nakon logina
    await ucitajTermine();
    await ucitajMojePrijave();
  } catch (error) {
    setMessage(`Login nije uspio: ${error.message}`, "error");
  } finally {
    setButtonLoading(loginSubmitButton, false);
  }
}

function renderLoggedOut() {
  if (currentUserBox) {
    currentUserBox.textContent = "Niste prijavljeni.";
    currentUserBox.classList.remove("logged-in");
  }

  if (navbarCurrentUser) {
    navbarCurrentUser.textContent = "Niste prijavljeni";
    navbarCurrentUser.classList.remove("logged-in");
  }
}

function renderLoggedIn(user) {
  const displayName = getUserDisplayName(user);
  const role = user.role ?? "unknown";

  if (currentUserBox) {
    currentUserBox.textContent = formatUser(user);
    currentUserBox.classList.add("logged-in");
  }

  if (navbarCurrentUser) {
    navbarCurrentUser.textContent = `Prijavljen: ${displayName} (${role})`;
    navbarCurrentUser.classList.add("logged-in");
  }
}

async function loadCurrentUser(options = {}) {
  const token = getToken();

  if (!token) {
    renderLoggedOut();
    return null;
  }

  const tokenUser = userFromToken(token);
  if (tokenUser) {
    renderLoggedIn(tokenUser);
  }

  try {
    const user = await apiFetch("/auth/me");
    renderLoggedIn(user);
    return user;
  } catch (error) {
    if (options.keepTokenFallback && tokenUser && error.status !== 401) {
      setMessage(`GET /auth/me nije uspio, ali token postoji: ${error.message}`, "info");
      return tokenUser;
    }

    clearToken();
    renderLoggedOut();
    setMessage(`Sesija nije vazeca: ${error.message}`, "error");
    return null;
  }
}

function logoutUser() {
  clearToken();
  renderLoggedOut();
  setMessage("Odjavljeni ste.", "ok");
}

async function loadTermsPreview() {
  await ucitajTermine();
}

function setupAuthUi() {
  if (scriptStatus) {
    scriptStatus.textContent = "Frontend script je ucitan. Forme se ne salju kao GET query string.";
    scriptStatus.dataset.type = "ok";
  }

  healthButton?.addEventListener("click", testHealth);
  refreshUserButton?.addEventListener("click", () => loadCurrentUser());
  registerForm?.addEventListener("submit", registerUser);
  registerSubmitButton?.addEventListener("click", registerUser);
  loginForm?.addEventListener("submit", loginUser);
  loginSubmitButton?.addEventListener("click", loginUser);
  logoutButton?.addEventListener("click", logoutUser);
  loadTermsButton?.addEventListener("click", loadTermsPreview);

  loadCurrentUser().then((user) => {
    if (user) {
      ucitajTermine();
      ucitajMojePrijave();
    }
  });
}

setupAuthUi();

// Privremeno izlozeno za lakse testiranje iz browser konzole.
window.appApi = {
  apiFetch,
  clearToken,
  getToken,
  loadCurrentUser,
  setToken,
};

// ============================================================
// Osoba 4 – Termini s prijavom/odjavom
// ============================================================

function formatDateTime(iso) {
  if (!iso) return "?";
  return new Date(iso).toLocaleString("hr-HR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function ucitajTermine() {
  const lista = document.querySelector("#termini-lista");
  const preEl = document.querySelector("#terms-result");
  if (!lista) return;

  lista.innerHTML = "<p class='muted'>Učitavanje termina…</p>";
  if (preEl) preEl.style.display = "none";

  try {
    const termini = await apiFetch("/termini");

    if (!termini.length) {
      lista.innerHTML = "<p class='muted'>Nema dostupnih termina.</p>";
      return;
    }

    // Dohvati prijave trenutnog studenta
    let mojaPrijavaIds = new Set();
    try {
      const moje = await apiFetch("/me/prijave");
      mojaPrijavaIds = new Set(moje.map((p) => p.termin?.term_id));
    } catch (_) {}

    lista.innerHTML = "";

    for (const termin of termini) {
      const prijavljen = mojaPrijavaIds.has(termin.term_id);

      let popTekst = "";
      let popunjen = false;
      try {
        const pop = await apiFetch(`/termini/${termin.term_id}/popunjenost`);
        popTekst = `Slobodna mjesta: ${pop.free_places} / ${pop.capacity}`;
        popunjen = pop.full;
        if (popunjen) popTekst += " 🔴 POPUNJENO";
      } catch (_) {
        popTekst = "Kapacitet nije dostupan";
      }

      const card = document.createElement("article");
      card.className = "card";
      card.style.cssText = "margin-bottom:0.75rem;padding:1rem;";
      card.innerHTML = `
        <strong>Termin #${termin.term_id}</strong><br/>
        Profesor ID: ${termin.professor_id} &nbsp;|&nbsp; Predmet ID: ${termin.subject_id}<br/>
        🕐 ${formatDateTime(termin.start_time)} – ${formatDateTime(termin.end_time)}<br/>
        <span class="muted" id="pop-${termin.term_id}">${popTekst}</span><br/>
        <button
          class="prijava-btn"
          data-id="${termin.term_id}"
          data-prijavljen="${prijavljen}"
          style="margin-top:0.5rem;width:auto;padding:0.5rem 1rem;"
          ${!prijavljen && popunjen ? "disabled" : ""}
        >${prijavljen ? "❌ Odjavi se" : "✔ Prijavi se"}</button>
        <span class="prijava-status" style="margin-left:0.5rem;font-size:0.875rem;"></span>
      `;
      lista.appendChild(card);
    }

    lista.querySelectorAll(".prijava-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const termId = Number(btn.dataset.id);
        const prijavljen = btn.dataset.prijavljen === "true";
        const statusEl = btn.nextElementSibling;

        btn.disabled = true;
        statusEl.textContent = "…";

        try {
          if (prijavljen) {
            await apiFetch(`/termini/${termId}/prijava`, { method: "DELETE" });
            statusEl.textContent = "✔ Odjavljeni ste.";
            btn.textContent = "✔ Prijavi se";
            btn.dataset.prijavljen = "false";
          } else {
            await apiFetch(`/termini/${termId}/prijava`, { method: "POST" });
            statusEl.textContent = "✔ Prijavljeni ste!";
            btn.textContent = "❌ Odjavi se";
            btn.dataset.prijavljen = "true";
          }
          btn.disabled = false;
          await ucitajMojePrijave();
        } catch (err) {
          statusEl.textContent = `✖ ${err.message}`;
          btn.disabled = false;
        }
      });
    });
  } catch (err) {
    lista.innerHTML = `<p style="color:#dc2626">Greška: ${err.message}</p>`;
  }
}

// ============================================================
// Osoba 4 – Moje prijave
// ============================================================

async function ucitajMojePrijave() {
  const lista = document.querySelector("#prijave-lista");
  if (!lista) return;

  lista.innerHTML = "<p class='muted'>Učitavanje…</p>";

  try {
    const prijave = await apiFetch("/me/prijave");

    if (!prijave.length) {
      lista.innerHTML = "<p class='muted'>Niste prijavljeni ni na jedan termin.</p>";
      return;
    }

    lista.innerHTML = "";
    prijave.forEach((p) => {
      const t = p.termin;
      const row = document.createElement("div");
      row.style.cssText = "border-bottom:1px solid #dfe5ef;padding:0.6rem 0;";
      row.innerHTML = t
        ? `<strong>Termin #${t.term_id}</strong> —
           ${formatDateTime(t.start_time)} do ${formatDateTime(t.end_time)}<br/>
           <span class="muted">Profesor ID: ${t.professor_id} | Predmet ID: ${t.subject_id}</span><br/>
           <span class="muted">Prijavljeno: ${formatDateTime(p.registered_at)}</span>`
        : `<span class="muted">Termin je obrisan (registration_id: ${p.registration_id})</span>`;
      lista.appendChild(row);
    });
  } catch (err) {
    lista.innerHTML = `<p style="color:#dc2626">Greška: ${err.message}</p>`;
  }
}

// ============================================================
// Osoba 4 – hookanje na postojeće event listenere
// ============================================================

document.querySelector("#load-terms-button")?.addEventListener("click", ucitajTermine);
document.querySelector("#load-prijave-btn")?.addEventListener("click", ucitajMojePrijave);

// Proširi window.appApi s Osoba 4 funkcijama
if (window.appApi) {
  window.appApi.ucitajTermine = ucitajTermine;
  window.appApi.ucitajMojePrijave = ucitajMojePrijave;
}
