"""Load processed Parquet and expose query / vocabulary helpers."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from zomato_rec.config import Settings, get_settings
from zomato_rec.data.ingest import SCHEMA_VERSION

logger = logging.getLogger(__name__)


class DataNotPreparedError(FileNotFoundError):
    """Raised when the processed Parquet/metadata cache is missing."""

    def __init__(self, path: Path):
        super().__init__(
            f"Processed data not found at {path}. "
            "Run: python scripts/prepare_dataset.py"
        )


def _require_file(path: Path) -> Path:
    if not path.is_file():
        raise DataNotPreparedError(path)
    return path


@lru_cache(maxsize=1)
def load_restaurants(data_path: str | None = None) -> pd.DataFrame:
    """Load the cleaned restaurants table (cached in-process)."""
    settings = get_settings()
    path = Path(data_path) if data_path else settings.data_path
    _require_file(path)
    frame = pd.read_parquet(path)
    logger.info("Loaded %s restaurants from %s", len(frame), path)
    return frame


@lru_cache(maxsize=1)
def load_metadata(metadata_path: str | None = None) -> dict[str, Any]:
    """Load ingest metadata JSON (locations, cuisines, counts)."""
    settings = get_settings()
    path = Path(metadata_path) if metadata_path else settings.metadata_path
    _require_file(path)
    return json.loads(path.read_text())


def clear_cache() -> None:
    """Clear in-process DataFrame / metadata caches (useful in tests)."""
    load_restaurants.cache_clear()
    load_metadata.cache_clear()


def list_locations(*, settings: Settings | None = None) -> list[str]:
    """Unique location values for UI dropdowns."""
    meta = load_metadata(str(settings.metadata_path) if settings else None)
    return list(meta.get("locations", []))


def list_cuisines(*, settings: Settings | None = None) -> list[str]:
    """Cuisine vocabulary for UI dropdowns."""
    meta = load_metadata(str(settings.metadata_path) if settings else None)
    return list(meta.get("cuisines", []))


def list_listed_in_cities(*, settings: Settings | None = None) -> list[str]:
    """Broader city/area grouping values."""
    meta = load_metadata(str(settings.metadata_path) if settings else None)
    return list(meta.get("listed_in_cities", []))


def get_restaurant_by_id(restaurant_id: int) -> pd.Series | None:
    """Return a single restaurant row by ``id``, or ``None``."""
    frame = load_restaurants()
    matches = frame.loc[frame["id"] == restaurant_id]
    if matches.empty:
        return None
    return matches.iloc[0]


def assert_schema_compatible(metadata: dict[str, Any] | None = None) -> None:
    """Warn or raise if cached metadata schema is older than the code."""
    meta = metadata or load_metadata()
    version = int(meta.get("schema_version", 0))
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"Processed data schema_version={version} is incompatible with "
            f"code schema_version={SCHEMA_VERSION}. "
            "Re-run: python scripts/prepare_dataset.py --force"
        )
