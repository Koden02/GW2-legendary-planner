from __future__ import annotations

from html import escape

from gw2_legendary_planner import __version__


def render_api_key_setup_html(*, app_name: str = "GW2 Legendary Planner") -> str:
    """Render the local first-run API key setup page."""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(app_name)} - Setup</title>
  <style>
{_SETUP_CSS}
  </style>
</head>
<body>
  <main class="setup-shell">
    <section class="setup-panel" aria-labelledby="setup-title">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">GW2</div>
        <div>
          <p class="eyebrow">Account Setup</p>
          <h1 id="setup-title">{escape(app_name)}</h1>
        </div>
      </div>
      <form data-api-key-form>
        <label for="api-key">Guild Wars 2 API key</label>
        <div class="key-row">
          <input
            id="api-key"
            name="api_key"
            type="password"
            autocomplete="off"
            spellcheck="false"
            required
            data-api-key-input
          >
          <button type="submit" data-api-key-submit>Load Account</button>
        </div>
        <label class="remember-row" for="remember-api-key">
          <input
            id="remember-api-key"
            name="remember_api_key"
            type="checkbox"
            data-remember-api-key
          >
          <span>Remember this key on this computer</span>
        </label>
        <p class="hint">
          By default, the key is kept in memory for this session only. If remembered,
          it is stored in the local GW2 Legendary Planner profile file as plaintext.
        </p>
        <p class="setup-error" data-setup-error hidden></p>
      </form>
      <footer>
        <span>Version {escape(__version__)}</span>
        <span>Local setup</span>
      </footer>
    </section>
  </main>
  <script>
{_SETUP_JS}
  </script>
</body>
</html>
"""


_SETUP_CSS = """
:root {
  color-scheme: light;
  --bg: #f5f7f4;
  --surface: #ffffff;
  --text: #1d2520;
  --muted: #66736b;
  --line: #d8e0da;
  --accent: #1b7f6b;
  --accent-strong: #105f51;
  --danger: #b94b4b;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, "Segoe UI", Arial, sans-serif;
  line-height: 1.45;
}

.setup-shell {
  width: min(720px, calc(100% - 32px));
}

.setup-panel {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  padding: 22px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 22px;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border: 1px solid #0f4f44;
  background: #123b35;
  color: #f3df9f;
  font-weight: 800;
  border-radius: 8px;
}

.eyebrow {
  margin: 0 0 4px;
  color: var(--accent-strong);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: 1.7rem;
  line-height: 1.1;
}

label {
  display: block;
  margin-bottom: 8px;
  font-weight: 800;
}

.key-row {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) auto;
  gap: 10px;
}

input {
  min-height: 42px;
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
  color: var(--text);
  font: inherit;
}

input:focus {
  border-color: var(--accent);
  outline: 2px solid rgb(27 127 107 / 18%);
}

button {
  min-height: 42px;
  border: 1px solid var(--accent);
  border-radius: 8px;
  background: var(--accent);
  color: white;
  cursor: pointer;
  font: inherit;
  font-weight: 800;
  padding: 8px 12px;
}

button:disabled {
  cursor: wait;
  opacity: 0.72;
}

.hint {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 0.88rem;
}

.remember-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 0 0;
  font-weight: 700;
}

.remember-row input {
  min-height: 0;
  width: 18px;
  height: 18px;
  accent-color: var(--accent);
}

.setup-error {
  margin: 12px 0 0;
  color: var(--danger);
  font-weight: 800;
}

.setup-error[hidden] {
  display: none;
}

footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 20px;
  color: var(--muted);
  font-size: 0.82rem;
}

footer span {
  padding: 6px 9px;
  border: 1px solid var(--line);
  border-radius: 8px;
}

@media (max-width: 640px) {
  .key-row {
    grid-template-columns: 1fr;
  }

  .setup-panel {
    padding: 16px;
  }
}
"""


_SETUP_JS = """
(function () {
  const form = document.querySelector("[data-api-key-form]");
  const input = document.querySelector("[data-api-key-input]");
  const remember = document.querySelector("[data-remember-api-key]");
  const submit = document.querySelector("[data-api-key-submit]");
  const error = document.querySelector("[data-setup-error]");

  function showError(message) {
    if (!error) {
      return;
    }
    error.textContent = message;
    error.hidden = false;
  }

  if (!form || !input || !submit) {
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const apiKey = input.value.trim();
    if (!apiKey) {
      showError("API key is required.");
      return;
    }

    submit.disabled = true;
    submit.textContent = "Loading";
    if (error) {
      error.hidden = true;
      error.textContent = "";
    }

    try {
      const response = await fetch("/api/setup/api-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: apiKey,
          remember_api_key: Boolean(remember && remember.checked),
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.error || "Account load failed.");
      }
      window.location.replace("/");
    } catch (setupError) {
      submit.disabled = false;
      submit.textContent = "Load Account";
      showError(setupError instanceof Error ? setupError.message : String(setupError));
    }
  });
})();
"""
