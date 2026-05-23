// Minimalni frontend helperi.
// TODO osoba 1: login/register treba spremati token pomocu setToken(token).
// TODO osoba 3: admin UI treba koristiti apiFetch("/termini", ...).
// TODO osoba 4: prijava/odjava treba koristiti apiFetch("/termini/{id}/prijava", ...).

const healthButton = document.querySelector("#health-button");
const healthResult = document.querySelector("#health-result");

function getToken() {
  return localStorage.getItem("access_token");
}

function setToken(token) {
  localStorage.setItem("access_token", token);
}

function clearToken() {
  localStorage.removeItem("access_token");
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
    throw new Error(message);
  }

  return data;
}

async function testHealth() {
  healthResult.textContent = "Ucitavanje...";

  try {
    const data = await apiFetch("/health");
    healthResult.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    healthResult.textContent = `Greska: ${error.message}`;
  }
}

healthButton?.addEventListener("click", testHealth);

// Privremeno izlozeno za lakse testiranje iz browser konzole.
window.appApi = {
  apiFetch,
  getToken,
  setToken,
  clearToken,
};
