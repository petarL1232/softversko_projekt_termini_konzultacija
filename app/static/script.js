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
  if (!termsResult) {
    return;
  }

  termsResult.textContent = "Ucitavanje termina...";

  try {
    const terms = await apiFetch("/termini");
    termsResult.textContent = JSON.stringify(terms, null, 2);
  } catch (error) {
    termsResult.textContent = `Termini nisu dostupni: ${error.message}`;
  }
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

  loadCurrentUser();
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
