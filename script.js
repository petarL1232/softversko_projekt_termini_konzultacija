// ============================================================
// Zajednički API helperi (osobe 1–5 koriste ove funkcije)
// ============================================================

function getToken() {
  return localStorage.getItem("access_token");
}

function setToken(token) {
  localStorage.setItem("access_token", token);
}

function clearToken() {
  localStorage.removeItem("access_token");
}

/**
 * Wrapper oko fetch koji automatski dodaje Bearer token i
 * baca Error ako odgovor nije 2xx.
 */
async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message = data?.detail || data?.message || "API greška";
    throw new Error(message);
  }

  return data;
}

// ============================================================
// Pomoćne UI funkcije
// ============================================================

function showResult(el, text, isError = false) {
  el.textContent = text;
  el.classList.remove("hidden");
  el.style.background = isError ? "#7f1d1d" : "#0f172a";
}

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

// ============================================================
// Health check
// ============================================================

const healthButton = document.querySelector("#health-button");
const healthResult = document.querySelector("#health-result");

async function testHealth() {
  healthResult.textContent = "Učitavanje...";
  try {
    const data = await apiFetch("/health");
    healthResult.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    healthResult.textContent = `Greška: ${err.message}`;
  }
}

healthButton?.addEventListener("click", testHealth);

// ============================================================
// Auth – Login
// ============================================================

document.querySelector("#login-button")?.addEventListener("click", async () => {
  const email = document.querySelector("#login-email").value.trim();
  const password = document.querySelector("#login-password").value;
  const resultEl = document.querySelector("#login-result");

  try {
    const formBody = new URLSearchParams({ username: email, password });
    const response = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formBody,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data?.detail || "Login greška");

    setToken(data.access_token);
    showResult(resultEl, `✔ Prijavljeni ste!\nToken: ${data.access_token.slice(0, 30)}…`);
    onLogin();
  } catch (err) {
    showResult(resultEl, `✖ ${err.message}`, true);
  }
});

// ============================================================
// Auth – Register
// ============================================================

document.querySelector("#register-button")?.addEventListener("click", async () => {
  const resultEl = document.querySelector("#register-result");
  try {
    const data = await apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        first_name: document.querySelector("#reg-first").value.trim(),
        last_name: document.querySelector("#reg-last").value.trim(),
        email: document.querySelector("#reg-email").value.trim(),
        password: document.querySelector("#reg-password").value,
      }),
    });
    showResult(resultEl, `✔ Registrirani ste!\nEmail: ${data.email}`);
  } catch (err) {
    showResult(resultEl, `✖ ${err.message}`, true);
  }
});

// ============================================================
// Osoba 4 – Termini lista s prijavom/odjavom
// ============================================================

/**
 * Dohvati sve termine i prikaži ih s gumbom za prijavu/odjavu/popunjenost.
 */
async function ucitajTermine() {
  const lista = document.querySelector("#termini-lista");
  lista.innerHTML = "<p class='muted'>Učitavanje…</p>";

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
    } catch (_) {
      // Zanemarujem ako ne uspije
    }

    lista.innerHTML = "";

    for (const termin of termini) {
      const prijavljen = mojaPrijavaIds.has(termin.term_id);

      let popunjenostTekst = "";
      try {
        const pop = await apiFetch(`/termini/${termin.term_id}/popunjenost`);
        popunjenostTekst = `Slobodna mjesta: ${pop.free_places} / ${pop.capacity}`;
        if (pop.full) popunjenostTekst += " 🔴 POPUNJENO";
      } catch (_) {
        popunjenostTekst = "Kapacitet nije dostupan";
      }

      const card = document.createElement("div");
      card.className = "termin-card card";
      card.style.marginBottom = "0.75rem";
      card.innerHTML = `
        <strong>Termin #${termin.term_id}</strong><br/>
        Profesor ID: ${termin.professor_id} &nbsp;|&nbsp; Predmet ID: ${termin.subject_id}<br/>
        🕐 ${formatDateTime(termin.start_time)} – ${formatDateTime(termin.end_time)}<br/>
        <span class="muted">${popunjenostTekst}</span><br/>
        <button class="prijava-btn" data-id="${termin.term_id}" data-prijavljen="${prijavljen}" style="margin-top:0.5rem">
          ${prijavljen ? "❌ Odjavi se" : "✔ Prijavi se"}
        </button>
        <span class="prijava-status" style="margin-left:0.5rem"></span>
      `;
      lista.appendChild(card);
    }

    // Dodaj event listenere na gumbe
    lista.querySelectorAll(".prijava-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const termId = Number(btn.dataset.id);
        const prijavljen = btn.dataset.prijavljen === "true";
        const statusEl = btn.nextElementSibling;

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
          // Osvježi i moje prijave
          await ucitajMojePrijave();
        } catch (err) {
          statusEl.textContent = `✖ ${err.message}`;
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
      row.style.cssText = "border-bottom:1px solid #dfe5ef;padding:0.5rem 0;";
      row.innerHTML = t
        ? `<strong>Termin #${t.term_id}</strong> – 
           ${formatDateTime(t.start_time)} do ${formatDateTime(t.end_time)}<br/>
           <span class="muted">Profesor ID: ${t.professor_id} | Predmet ID: ${t.subject_id}</span><br/>
           <span class="muted">Prijavili ste se: ${formatDateTime(p.registered_at)}</span>`
        : `<span class="muted">Termin je obrisan (registration_id: ${p.registration_id})</span>`;
      lista.appendChild(row);
    });
  } catch (err) {
    lista.innerHTML = `<p style="color:#dc2626">Greška: ${err.message}</p>`;
  }
}

// ============================================================
// Stanje UI ovisno o tome je li korisnik prijavljen
// ============================================================

function onLogin() {
  document.querySelector("#termini-hint").style.display = "none";
  document.querySelector("#load-termini-btn").style.display = "block";
  document.querySelector("#prijave-hint").style.display = "none";
  document.querySelector("#load-prijave-btn").style.display = "block";

  ucitajTermine();
  ucitajMojePrijave();
}

document
  .querySelector("#load-termini-btn")
  ?.addEventListener("click", ucitajTermine);

document
  .querySelector("#load-prijave-btn")
  ?.addEventListener("click", ucitajMojePrijave);

// Ako token već postoji (npr. stranica je reloadana), odmah prikaži sadržaj
if (getToken()) {
  onLogin();
}

// ============================================================
// Privremeno izloženo za lako testiranje iz browser konzole
// ============================================================
window.appApi = {
  apiFetch,
  getToken,
  setToken,
  clearToken,
  ucitajTermine,
  ucitajMojePrijave,
};
