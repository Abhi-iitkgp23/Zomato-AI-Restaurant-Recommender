#!/usr/bin/env python3
"""CLI demo for the Phase 2 recommend path (no Streamlit).

Examples:
  python scripts/recommend_cli.py --location Banashankari --cuisine Italian --budget medium
  python scripts/recommend_cli.py --location Koramangala --cuisine Chinese --no-llm
"""

from __future__ import annotations

import argparse
import json
import logging
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recommend restaurants (filter + LLM).")
    parser.add_argument("--location", default=None)
    parser.add_argument("--cuisine", default=None)
    parser.add_argument(
        "--budget",
        choices=["low", "medium", "high"],
        default=None,
    )
    parser.add_argument("--min-rating", type=float, default=None)
    parser.add_argument("--prefs", default=None, help="Additional free-text preferences")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Force heuristic fallback (no LLM call).",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON response.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    from zomato_rec.models import Preferences
    from zomato_rec.services.recommend import recommend

    try:
        preferences = Preferences(
            location=args.location,
            cuisine=args.cuisine,
            budget=args.budget,
            min_rating=args.min_rating,
            additional_preferences=args.prefs,
            top_n=args.top_n,
        )
    except Exception as exc:
        print(f"Invalid preferences: {exc}", file=sys.stderr)
        return 2

    result = recommend(preferences, use_llm=not args.no_llm)

    if args.json:
        print(result.model_dump_json(indent=2))
        return 0

    print(f"Summary: {result.summary}")
    print(
        f"Candidates: {result.filter_meta.candidate_count} "
        f"(from {result.filter_meta.total_before_cap} before cap)"
    )
    if result.filter_meta.notices:
        print("Notices:", "; ".join(result.filter_meta.notices))
    if result.used_fallback:
        print(f"Fallback: {result.fallback_reason}")
    if result.latency_ms is not None:
        print(f"Latency: {result.latency_ms:.0f} ms")
    print()
    for item in result.recommendations:
        cost = (
            f"₹{int(item.cost_for_two)}"
            if item.cost_for_two is not None
            else "N/A"
        )
        rating = item.rating if item.rating is not None else "N/A"
        print(f"{item.rank}. {item.name}  [{item.cuisine}]")
        print(f"   rating={rating}  cost_for_two={cost}  location={item.location}")
        print(f"   {item.explanation}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
