"""Deployment config sanity checks (Railway + Vercel)."""

from __future__ import annotations

import json
import re

import pytest

from zomato_rec.config import PROJECT_ROOT

pytest.importorskip("fastapi")

from fastapi.routing import APIRoute

from zomato_rec.app.api import app


def _vercel_rewrite_matches(sources: list[str], path: str) -> bool:
    for source in sources:
        pattern = "^" + re.sub(r":\w+\*", ".*", source) + "$"
        if re.match(pattern, path):
            return True
    return False


def test_vercel_rewrites_cover_every_api_route():
    config = json.loads((PROJECT_ROOT / "frontend" / "vercel.json").read_text())
    rewrites = config["rewrites"]
    sources = [r["source"] for r in rewrites]

    api_paths = [route.path for route in app.routes if isinstance(route, APIRoute)]
    assert api_paths
    missing = [p for p in api_paths if not _vercel_rewrite_matches(sources, p)]
    assert not missing, f"Add Vercel rewrites for: {missing}"

    for path in ("/docs", "/openapi.json"):
        assert _vercel_rewrite_matches(sources, path)

    for rewrite in rewrites:
        assert rewrite["destination"].startswith("https://")


def test_railway_start_command_binds_public_port():
    config = json.loads((PROJECT_ROOT / "railway.json").read_text())
    start = config["deploy"]["startCommand"]
    assert "zomato_rec.app.api:app" in start
    assert "--host 0.0.0.0" in start
    assert "$PORT" in start
    assert config["deploy"]["healthcheckPath"] == "/health"


def test_python_version_pinned_to_supported_release():
    version = (PROJECT_ROOT / ".python-version").read_text().strip()
    major, minor = (int(part) for part in version.split(".")[:2])
    assert (major, minor) >= (3, 11)
