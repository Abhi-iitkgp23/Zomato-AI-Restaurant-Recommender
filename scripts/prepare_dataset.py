#!/usr/bin/env python3
"""One-shot dataset ingestion CLI.

Usage:
  python scripts/prepare_dataset.py
  python scripts/prepare_dataset.py --force
"""

from __future__ import annotations

import argparse
import logging
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download, clean, and cache the Zomato HF restaurant dataset."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild Parquet/metadata even if a cache already exists.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    from zomato_rec.data.ingest import prepare_dataset
    from zomato_rec.data.repository import clear_cache, load_metadata

    data_path, metadata_path = prepare_dataset(force=args.force)
    clear_cache()
    meta = load_metadata(str(metadata_path))

    print(f"Parquet:   {data_path}")
    print(f"Metadata:  {metadata_path}")
    print(f"Rows:      {meta.get('row_count')}")
    print(f"Locations: {len(meta.get('locations', []))}")
    print(f"Cuisines:  {len(meta.get('cuisines', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
