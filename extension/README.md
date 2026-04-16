# FocusSight AI – Browser Extension (Phase 14)

A Manifest V3 Chrome / Firefox browser extension that reads live focus state
from the **Phase 13 local API server** and surfaces non-intrusive in-browser
nudges — no cloud, no subscription.

---

## Prerequisites

1. The Python tracker is running **with the `--serve` flag**:

   ```bash
   python eye_test.py --autolog --serve
   ```

   This starts the FocusSight webcam tracker **and** the local API server on
   `http://127.0.0.1:8765`.

2. Install the server dependencies if you haven't already:

   ```bash
   pip install "focussight-ai[server]"
   # or: pip install fastapi uvicorn[standard] websockets
   ```

---

## Loading the extension (Chrome / Edge — unpacked)

1. Open `chrome://extensions` in your browser.
2. Enable **Developer mode** (top-right toggle).
3. Click **Load unpacked** and select this `extension/` folder.
4. The FocusSight badge appears in the toolbar.

---

## Loading the extension (Firefox — temporary)

1. Open `about:debugging#/runtime/this-firefox`.
2. Click **Load Temporary Add-on**.
3. Select `extension/manifest.json`.

---

## Icon assets

The extension references PNG icons at:

```
icons/icon16.png
icons/icon32.png
icons/icon48.png
icons/icon128.png
```

Placeholder 1 × 1 transparent PNGs are included so the extension loads
without errors.  Replace them with real artwork before publishing to a
browser store.

A helper script is provided to regenerate placeholders:

```bash
python generate_icons.py
```

---

## Packaging for distribution

Run the helper script from the repo root:

```bash
python extension/package_extension.py
```

This produces:
- `dist/focussight-extension.zip` — ready for Chrome Web Store submission
- `dist/focussight-extension.xpi` — unsigned Firefox add-on

---

## Options

Click **Options** in the popup or open the extensions page and click
"Extension options" to configure:

| Setting | Default | Description |
|---|---|---|
| API Server URL | `http://127.0.0.1:8765` | URL of the local FocusSight server |
| Notification Style | Banner | `banner`, `silent` (badge only), or `none` |
| Distraction Threshold | 5 s | Seconds of distraction before a notification fires |

---

## Badge colours

| Colour | Meaning |
|---|---|
| 🟢 Green | FOCUSED |
| 🔴 Red | DISTRACTED |
| 🟡 Amber | Server reachable but state is UNKNOWN / degraded signal |
| ⚫ Grey | Server not reachable |
