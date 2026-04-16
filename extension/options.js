"use strict";

const DEFAULTS = {
  serverUrl: "http://127.0.0.1:8765",
  notificationStyle: "banner",
  distractionThresholdSeconds: 5,
};

function el(id) { return document.getElementById(id); }

// Load saved settings into the form.
chrome.storage.sync.get(DEFAULTS, (settings) => {
  el("server-url").value    = settings.serverUrl;
  el("notif-style").value   = settings.notificationStyle;
  el("dist-threshold").value = settings.distractionThresholdSeconds;
});

// Save settings.
el("save-btn").addEventListener("click", () => {
  const serverUrl = (el("server-url").value || "").trim() || DEFAULTS.serverUrl;
  const notificationStyle = el("notif-style").value;
  const distractionThresholdSeconds = Math.max(
    1,
    Math.min(120, parseInt(el("dist-threshold").value, 10) || DEFAULTS.distractionThresholdSeconds)
  );

  chrome.storage.sync.set(
    { serverUrl, notificationStyle, distractionThresholdSeconds },
    () => {
      const msg = el("status-msg");
      msg.textContent = "Saved!";
      setTimeout(() => { msg.textContent = ""; }, 2000);
    }
  );
});
