"use strict";

// ── Helpers ───────────────────────────────────────────────────────────────────

function el(id) { return document.getElementById(id); }

function fmtSeconds(s) {
  s = Math.round(s || 0);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}m ${sec.toString().padStart(2, "0")}s`;
}

/** Format a percentage value (0-100 range) for display. */
function fmtPct(v) {
  return `${Math.round(v || 0)}%`;
}

// ── Render ────────────────────────────────────────────────────────────────────

function render(status) {
  const state = (status.state || "UNKNOWN").toUpperCase();

  // Badge
  const badge = el("state-badge");
  badge.textContent = state;
  badge.className = ""; // reset
  if (state === "FOCUSED")    badge.classList.add("badge-focused");
  else if (state === "DISTRACTED") badge.classList.add("badge-distracted");
  else                         badge.classList.add("badge-unknown");

  // Stats
  el("focus-pct").textContent   = fmtPct(status.avg_focus_pct);
  el("dist-pct").textContent    = fmtPct(status.distracted_pct);
  el("streak").textContent      = fmtSeconds(status.focused_streak_seconds);
  el("elapsed").textContent     = fmtSeconds(status.elapsed_seconds);

  // Progress bar
  const pct = Math.min(100, Math.round((status.focus_score || 0) * 100));
  const bar = el("focus-bar");
  bar.style.width = pct + "%";
  bar.style.background = state === "FOCUSED" ? "#27ae60"
                        : state === "DISTRACTED" ? "#e74c3c"
                        : "#f39c12";

  // Signal
  el("signal-status").textContent = status.signal_status || "–";

  // Live indicator
  el("live-dot").className = "dot live";
  el("live-label").textContent = "Live";
}

function renderOffline() {
  const badge = el("state-badge");
  badge.textContent = "Offline";
  badge.className = "badge-offline";
  el("live-dot").className = "dot";
  el("live-label").textContent = "Server not reachable";
  el("focus-pct").textContent = "–";
  el("dist-pct").textContent = "–";
  el("streak").textContent = "–";
  el("elapsed").textContent = "–";
  el("focus-bar").style.width = "0%";
  el("signal-status").textContent = "–";
}

// ── Fetch & poll ──────────────────────────────────────────────────────────────

async function getServerUrl() {
  return new Promise((resolve) => {
    chrome.storage.sync.get({ serverUrl: "http://127.0.0.1:8765" }, (s) => {
      resolve((s.serverUrl || "http://127.0.0.1:8765").replace(/\/$/, ""));
    });
  });
}

async function fetchStatus() {
  const url = await getServerUrl();
  try {
    const resp = await fetch(`${url}/status`, { signal: AbortSignal.timeout(2000) });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  } catch {
    return null;
  }
}

async function tick() {
  const status = await fetchStatus();
  if (status) render(status);
  else renderOffline();
}

// Poll while popup is open.
tick();
const timer = setInterval(tick, 1000);
window.addEventListener("unload", () => clearInterval(timer));

// Options link.
el("options-link").addEventListener("click", (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});
