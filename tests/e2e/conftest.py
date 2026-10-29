"""Shared fixtures and opaque-box test helpers for the Demo 1 E2E test suite."""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

import pytest

# Enforce mandatory mTLS guardrail before any Google Cloud imports
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))


class DummyToolContext:
    """Lightweight ADK ToolContext double exposing a mutable `.state` dictionary."""

    def __init__(self, initial_state: dict[str, Any] | None = None) -> None:
        self.state: dict[str, Any] = dict(initial_state) if initial_state else {}


@pytest.fixture
def workspace_root() -> Path:
    """Return the absolute path to the project workspace root."""
    return WORKSPACE_ROOT


@pytest.fixture
def dummy_tool_context() -> DummyToolContext:
    """Return a fresh DummyToolContext with an empty `.state` dict."""
    return DummyToolContext()


def load_dotenv_dict(dotenv_path: Path) -> dict[str, str]:
    """Parse a `.env` or `.env.example` file into a key-value dictionary."""
    assert dotenv_path.exists(), f"Expected env file at {dotenv_path}"
    env_map: dict[str, str] = {}
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        env_map[key] = val
    return env_map


def load_chat_app_module() -> Any:
    """Dynamically load `cloud_run_chat_app/main.py` as a module."""
    main_path = WORKSPACE_ROOT / "cloud_run_chat_app" / "main.py"
    assert main_path.exists(), f"Missing {main_path}"
    chat_dir = str(main_path.parent)
    if chat_dir not in sys.path:
        sys.path.insert(0, chat_dir)

    spec = importlib.util.spec_from_file_location("cloud_run_chat_app_main", main_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_cwd = os.getcwd()
    try:
        os.chdir(chat_dir)
        spec.loader.exec_module(module)
    finally:
        os.chdir(old_cwd)
    return module


@pytest.fixture
def chat_app_module() -> Any:
    """Load `cloud_run_chat_app/main.py` and reset its in-memory ticket store."""
    mod = load_chat_app_module()
    if hasattr(mod, "ACTIVE_TICKETS") and isinstance(mod.ACTIVE_TICKETS, list):
        mod.ACTIVE_TICKETS.clear()
    yield mod
    if hasattr(mod, "ACTIVE_TICKETS") and isinstance(mod.ACTIVE_TICKETS, list):
        mod.ACTIVE_TICKETS.clear()


@pytest.fixture
def chat_client(chat_app_module: Any) -> Any:
    """Return a FastAPI TestClient bound to `cloud_run_chat_app.main.app`."""
    from fastapi.testclient import TestClient

    client = TestClient(chat_app_module.app)
    client.post("/api/reset")
    return client
