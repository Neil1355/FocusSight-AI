"""FocusSight AI – Phase 13: Local REST API / WebSocket Server.

Starts a lightweight FastAPI server alongside the tracker so that browser
extensions and other local clients can read live focus state without
running Python themselves.

Install the optional server dependencies first:
    pip install "focussight-ai[server]"
    # or: pip install fastapi uvicorn[standard] websockets

Usage (via tracker CLI):
    python eye_test.py --autolog --serve

Usage (standalone, for testing without a webcam):
    python -m focussight.server
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

# ---------------------------------------------------------------------------
# Shared state: the tracker thread writes here; the API layer reads it.
# ---------------------------------------------------------------------------

@dataclass
class FocusState:
    """Snapshot of live tracker state shared between threads."""
    state: str = "UNKNOWN"          # FOCUSED | DISTRACTED | UNKNOWN
    focus_score: float = 0.0        # weighted focus score 0-1
    signal_status: str = "UNKNOWN"  # TRACKING_OK, LOW_LIGHT, etc.
    elapsed_seconds: float = 0.0    # seconds since session started
    focused_streak_seconds: float = 0.0  # current focused run length
    distracted_streak_seconds: float = 0.0
    avg_focus_pct: float = 0.0
    distracted_pct: float = 0.0
    reminder_policy: str = "balanced"
    logging_enabled: bool = False
    session_log_path: Optional[str] = None
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["updated_at"] = self.updated_at
        return d


# Module-level singleton; tracker updates this in-place each frame.
_live_state: FocusState = FocusState()
_state_lock: threading.Lock = threading.Lock()


def update_live_state(**kwargs) -> None:
    """Thread-safe update of the shared focus state (called from the tracker)."""
    with _state_lock:
        for key, value in kwargs.items():
            if hasattr(_live_state, key):
                setattr(_live_state, key, value)
        _live_state.updated_at = time.time()


def get_live_state() -> dict:
    """Return a snapshot of the current focus state (thread-safe)."""
    with _state_lock:
        return _live_state.to_dict()


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

def _build_app():
    """Build and return the FastAPI application.  Import is deferred so that
    importing focussight.server does not fail when FastAPI is not installed."""
    try:
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "FastAPI and uvicorn are required for the FocusSight server.\n"
            'Install with: pip install "focussight-ai[server]"\n'
            "or: pip install fastapi uvicorn[standard] websockets"
        ) from exc

    app = FastAPI(
        title="FocusSight AI",
        description="Local REST / WebSocket API for real-time focus state",
        version="0.14.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],           # browser extensions on localhost need this
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------ #
    # GET /status – latest focus state snapshot                           #
    # ------------------------------------------------------------------ #
    @app.get("/status")
    async def status():
        """Return the current focus state as JSON."""
        return JSONResponse(content=get_live_state())

    # ------------------------------------------------------------------ #
    # GET /report – last-session ops report JSON (if a log exists)        #
    # ------------------------------------------------------------------ #
    @app.get("/report")
    async def report():
        """Return the ops report for the most recent logged session."""
        snapshot = get_live_state()
        log_path = snapshot.get("session_log_path")
        if not log_path:
            return JSONResponse(
                content={"error": "No active or recent session log available."},
                status_code=404,
            )
        try:
            from focussight.ops_report import build_ops_report
            ops = build_ops_report(log_path)
            return JSONResponse(content=ops)
        except Exception:  # pragma: no cover
            return JSONResponse(
                content={"error": "Failed to build ops report for the active session."},
                status_code=500,
            )

    # ------------------------------------------------------------------ #
    # GET /health – simple liveness probe                                 #
    # ------------------------------------------------------------------ #
    @app.get("/health")
    async def health():
        return {"ok": True}

    # ------------------------------------------------------------------ #
    # WebSocket /events – streams a state event every second              #
    # ------------------------------------------------------------------ #
    @app.websocket("/events")
    async def events(websocket: WebSocket):
        """Stream focus-state events to connected clients once per second."""
        await websocket.accept()
        try:
            while True:
                snapshot = get_live_state()
                await websocket.send_json(snapshot)
                await asyncio.sleep(1.0)
        except WebSocketDisconnect:
            pass

    return app


# Lazily-initialised singleton so we can import the module without FastAPI.
_app = None


def get_app():
    """Return the FastAPI application instance (created on first call)."""
    global _app
    if _app is None:
        _app = _build_app()
    return _app


# ---------------------------------------------------------------------------
# Server lifecycle helpers
# ---------------------------------------------------------------------------

def start_server(host: str = "127.0.0.1", port: int = 8765) -> threading.Thread:
    """Start the uvicorn server in a daemon thread.

    Returns the thread so callers can join it if needed.  The server runs
    until the main process exits.
    """
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "uvicorn is required to start the FocusSight server.\n"
            'Install with: pip install "focussight-ai[server]"'
        ) from exc

    app = get_app()

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True, name="focussight-server")
    thread.start()
    # Give the server a moment to bind the port before returning.
    time.sleep(0.5)
    return thread


# ---------------------------------------------------------------------------
# CLI entry-point (python -m focussight.server)
# ---------------------------------------------------------------------------

def main():  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(
        description="FocusSight AI local API server (Phase 13)"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "uvicorn is required.  Install with: pip install 'focussight-ai[server]'"
        ) from exc

    print(f"FocusSight AI server starting on http://{args.host}:{args.port}")
    print("Endpoints: GET /status  GET /report  GET /health  WS /events")
    uvicorn.run(get_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
