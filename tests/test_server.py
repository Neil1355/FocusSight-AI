"""Tests for Phase 13: FocusSight local REST API server (focussight/server.py).

These tests exercise the shared-state helpers and the FastAPI endpoint
contracts without requiring a real webcam.  No external server process is
started; the FastAPI test client is used directly.
"""
import sys
import time
import unittest


# ---------------------------------------------------------------------------
# Import server module directly, bypassing focussight/__init__.py which
# transitively imports cv2 via tracker.  The server itself has no cv2 dep.
# ---------------------------------------------------------------------------
import importlib
import types


def _import_server():
    """Import focussight.server while bypassing the cv2 requirement in tracker."""
    import importlib.util
    import os
    server_path = os.path.join(os.path.dirname(__file__), "..", "focussight", "server.py")
    spec = importlib.util.spec_from_file_location("focussight.server", server_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["focussight.server"] = mod
    spec.loader.exec_module(mod)
    return mod


_server = _import_server()
FocusState = _server.FocusState
get_live_state = _server.get_live_state
update_live_state = _server.update_live_state


# ── Shared-state unit tests ───────────────────────────────────────────────────

class SharedStateTests(unittest.TestCase):
    def setUp(self):
        """Reset live state before each test."""
        _server._live_state = FocusState()

    def test_default_state_is_unknown(self):
        state = get_live_state()
        self.assertEqual(state["state"], "UNKNOWN")

    def test_update_live_state_changes_fields(self):
        update_live_state(state="FOCUSED", focus_score=0.87, signal_status="TRACKING_OK")
        snapshot = get_live_state()
        self.assertEqual(snapshot["state"], "FOCUSED")
        self.assertAlmostEqual(snapshot["focus_score"], 0.87)
        self.assertEqual(snapshot["signal_status"], "TRACKING_OK")

    def test_update_live_state_ignores_unknown_keys(self):
        """Extra keys should not raise; only known attrs are stored."""
        update_live_state(nonexistent_field="boom")
        snapshot = get_live_state()
        self.assertNotIn("nonexistent_field", snapshot)

    def test_updated_at_advances_on_update(self):
        before = get_live_state()["updated_at"]
        time.sleep(0.05)
        update_live_state(state="DISTRACTED")
        after = get_live_state()["updated_at"]
        self.assertGreater(after, before)

    def test_update_multiple_fields_at_once(self):
        update_live_state(
            state="DISTRACTED",
            focus_score=0.2,
            elapsed_seconds=120.0,
            distracted_streak_seconds=15.0,
        )
        snapshot = get_live_state()
        self.assertEqual(snapshot["state"], "DISTRACTED")
        self.assertAlmostEqual(snapshot["focus_score"], 0.2)
        self.assertAlmostEqual(snapshot["elapsed_seconds"], 120.0)
        self.assertAlmostEqual(snapshot["distracted_streak_seconds"], 15.0)

    def test_get_live_state_returns_dict(self):
        snapshot = get_live_state()
        self.assertIsInstance(snapshot, dict)
        for key in (
            "state", "focus_score", "signal_status", "elapsed_seconds",
            "focused_streak_seconds", "distracted_streak_seconds",
            "avg_focus_pct", "distracted_pct", "reminder_policy",
            "logging_enabled", "session_log_path", "updated_at",
        ):
            self.assertIn(key, snapshot)

    def test_focus_state_to_dict_roundtrip(self):
        fs = FocusState(
            state="FOCUSED",
            focus_score=0.9,
            signal_status="TRACKING_OK",
            elapsed_seconds=60.0,
            focused_streak_seconds=45.0,
            distracted_streak_seconds=0.0,
            avg_focus_pct=88.5,
            distracted_pct=11.5,
            reminder_policy="gentle",
            logging_enabled=True,
            session_log_path="/tmp/session.csv",
        )
        d = fs.to_dict()
        self.assertEqual(d["state"], "FOCUSED")
        self.assertEqual(d["focus_score"], 0.9)
        self.assertEqual(d["session_log_path"], "/tmp/session.csv")
        self.assertTrue(d["logging_enabled"])


# ── FastAPI endpoint tests (using TestClient) ─────────────────────────────────

try:
    from fastapi.testclient import TestClient
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi[testclient] not installed")
class ServerEndpointTests(unittest.TestCase):
    def setUp(self):
        _server._live_state = FocusState()
        _server._app = None  # force rebuild
        self.client = TestClient(_server.get_app())

    def test_health_returns_ok(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"ok": True})

    def test_status_returns_all_expected_keys(self):
        resp = self.client.get("/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        for key in ("state", "focus_score", "signal_status", "elapsed_seconds"):
            self.assertIn(key, data)

    def test_status_reflects_live_state_update(self):
        update_live_state(state="FOCUSED", focus_score=0.75)
        resp = self.client.get("/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["state"], "FOCUSED")
        self.assertAlmostEqual(data["focus_score"], 0.75)

    def test_report_returns_404_when_no_log(self):
        _server._live_state = FocusState(session_log_path=None)
        resp = self.client.get("/report")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("error", resp.json())

    def test_status_cors_header_present(self):
        resp = self.client.get("/status", headers={"Origin": "http://localhost:3000"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access-control-allow-origin", resp.headers)


if __name__ == "__main__":
    unittest.main()
