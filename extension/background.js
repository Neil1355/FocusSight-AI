/**
 * FocusSight AI – Background Service Worker (Phase 14)
 *
 * Polls GET /status from the local FocusSight API server every second
 * and updates the extension badge colour to reflect focus state:
 *   green  → FOCUSED
 *   amber  → UNKNOWN / LOW_CONFIDENCE / LOW_LIGHT / OCCLUDED
 *   red    → DISTRACTED
 *
 * Also fires a desktop notification when a distraction streak exceeds
 * the user-configured threshold (default: server alert_after_seconds).
 */

"use strict";

// ── Defaults ──────────────────────────────────────────────────────────────────
const DEFAULT_SERVER_URL = "http://127.0.0.1:8765";
const DEFAULT_POLL_INTERVAL_MS = 1000;
const DEFAULT_DISTRACTION_THRESHOLD_S = 5;
const DEFAULT_NOTIFICATION_STYLE = "banner"; // banner | silent | none

// ── State ─────────────────────────────────────────────────────────────────────
let lastNotifiedState = null;
let lastNotificationAt = 0;
const NOTIFICATION_COOLDOWN_MS = 10_000; // min 10 s between notifications

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Read current settings from chrome.storage.sync with defaults. */
async function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(
      {
        serverUrl: DEFAULT_SERVER_URL,
        notificationStyle: DEFAULT_NOTIFICATION_STYLE,
        distractionThresholdSeconds: DEFAULT_DISTRACTION_THRESHOLD_S,
      },
      resolve
    );
  });
}

/**
 * Map a focus state string to a badge background colour.
 * @param {string} state
 * @returns {string} hex colour
 */
function badgeColor(state) {
  if (state === "FOCUSED") return "#27ae60";    // green
  if (state === "DISTRACTED") return "#e74c3c"; // red
  return "#f39c12";                             // amber – UNKNOWN / degraded
}

/**
 * Update the toolbar badge text and colour.
 * @param {string} state
 * @param {number} focusPct  0-100
 */
function updateBadge(state, focusPct) {
  const label = state === "FOCUSED" ? "ON" : state === "DISTRACTED" ? "OFF" : "?";
  chrome.action.setBadgeText({ text: label });
  chrome.action.setBadgeBackgroundColor({ color: badgeColor(state) });
  chrome.action.setTitle({
    title: `FocusSight AI – ${state}  (focus ${Math.round(focusPct)}%)`,
  });
}

/** Fire a desktop notification (respects cooldown). */
function notify(title, message) {
  const now = Date.now();
  if (now - lastNotificationAt < NOTIFICATION_COOLDOWN_MS) return;
  lastNotificationAt = now;
  chrome.notifications.create("focussight-alert", {
    type: "basic",
    iconUrl: "icons/icon48.png",
    title,
    message,
    priority: 1,
  });
}

// ── Main polling loop ─────────────────────────────────────────────────────────

async function poll() {
  const settings = await getSettings();
  const url = (settings.serverUrl || DEFAULT_SERVER_URL).replace(/\/$/, "");
  const style = settings.notificationStyle || DEFAULT_NOTIFICATION_STYLE;
  const threshold = Number(settings.distractionThresholdSeconds) || DEFAULT_DISTRACTION_THRESHOLD_S;

  let status;
  try {
    const resp = await fetch(`${url}/status`, { signal: AbortSignal.timeout(2000) });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    status = await resp.json();
  } catch {
    // Server not reachable – show neutral badge.
    chrome.action.setBadgeText({ text: "–" });
    chrome.action.setBadgeBackgroundColor({ color: "#95a5a6" });
    chrome.action.setTitle({ title: "FocusSight AI – server not reachable" });
    return;
  }

  const state = status.state || "UNKNOWN";
  const focusPct = (status.focus_score || 0) * 100;
  const distractedStreak = status.distracted_streak_seconds || 0;

  updateBadge(state, focusPct);

  // Notifications
  if (style !== "none" && state === "DISTRACTED" && distractedStreak >= threshold) {
    if (lastNotifiedState !== "DISTRACTED") {
      lastNotifiedState = "DISTRACTED";
      if (style === "banner") {
        notify(
          "FocusSight – Distraction Alert",
          `You've been distracted for ${Math.round(distractedStreak)}s. Time to refocus!`
        );
      }
    }
  } else if (state === "FOCUSED") {
    lastNotifiedState = "FOCUSED";
  }
}

// ── Alarm-based scheduling ────────────────────────────────────────────────────

chrome.alarms.create("focussight-poll", { periodInMinutes: 1 / 60 }); // ~every 1 s

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "focussight-poll") poll();
});

// Run immediately on service-worker start.
poll();
