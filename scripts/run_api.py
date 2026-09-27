#!/usr/bin/env python3
"""Run the Phase 4 FastAPI server.

  uvicorn zomato_rec.app.api:app --reload --port 8000
  # or:
  python scripts/run_api.py
"""

from __future__ import annotations

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the recommend FastAPI server.")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "FastAPI/uvicorn not installed. Run: pip install -e '.[api]'"
        ) from exc

    uvicorn.run(
        "zomato_rec.app.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
