"""Hugging Face load, preprocess, and persist restaurant data."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
from datasets import load_dataset

from zomato_rec.config import Settings, get_settings
from zomato_rec.data.parsers import (
    budget_band,
    cuisine_tokens,
    normalize_cuisines,
    parse_cost_for_two,
    parse_rating,
)

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

# Lean columns kept in the processed Parquet (MVP).
KEEP_SOURCE_COLUMNS = [
    "name",
    "location",
    "listed_in(city)",
    "address",
    "url",
    "cuisines",
    "rate",
    "votes",
    "approx_cost(for two people)",
    "rest_type",
    "dish_liked",
    "online_order",
    "book_table",
]

OUTPUT_COLUMNS = [
    "id",
    "name",
    "location",
    "listed_in_city",
    "address",
    "url",
    "cuisines",
    "rating",
    "votes",
    "cost_for_two",
    "budget_band",
    "rest_type",
    "dish_liked",
    "online_order",
    "book_table",
]


def _as_str(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def _as_votes(value: Any) -> int:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def load_raw_dataframe(settings: Settings | None = None) -> pd.DataFrame:
    """Download (or use HF cache) and return the raw dataset as a DataFrame."""
    settings = settings or get_settings()
    kwargs: dict[str, Any] = {}
    if settings.hf_dataset_revision:
        kwargs["revision"] = settings.hf_dataset_revision

    logger.info(
        "Loading Hugging Face dataset %s (revision=%s)",
        settings.hf_dataset_id,
        settings.hf_dataset_revision or "default",
    )
    dataset = load_dataset(settings.hf_dataset_id, split="train", **kwargs)
    frame = dataset.to_pandas()
    logger.info("Loaded %s raw rows", len(frame))
    return frame


def preprocess_restaurants(
    raw: pd.DataFrame,
    *,
    low_max: int = 400,
    med_max: int = 800,
) -> pd.DataFrame:
    """Clean, normalize, deduplicate, and band the raw restaurant table."""
    if raw.empty:
        raise ValueError("Raw dataset is empty; cannot build processed Parquet")

    available = [col for col in KEEP_SOURCE_COLUMNS if col in raw.columns]
    missing = set(KEEP_SOURCE_COLUMNS) - set(available)
    if missing:
        logger.warning("Source columns missing from dataset: %s", sorted(missing))

    frame = raw.loc[:, available].copy()

    # Ensure optional source columns exist so downstream code is uniform.
    for col in KEEP_SOURCE_COLUMNS:
        if col not in frame.columns:
            frame[col] = None

    frame["name"] = frame["name"].map(_as_str)
    frame["location"] = frame["location"].map(_as_str)
    frame["listed_in_city"] = frame["listed_in(city)"].map(_as_str)
    frame["address"] = frame["address"].map(_as_str)
    frame["url"] = frame["url"].map(_as_str)
    frame["rest_type"] = frame["rest_type"].map(_as_str)
    frame["dish_liked"] = frame["dish_liked"].map(_as_str)
    frame["online_order"] = frame["online_order"].map(_as_str)
    frame["book_table"] = frame["book_table"].map(_as_str)

    frame["cuisines"] = frame["cuisines"].map(normalize_cuisines)
    frame["rating"] = frame["rate"].map(parse_rating)
    frame["cost_for_two"] = frame["approx_cost(for two people)"].map(parse_cost_for_two)
    frame["votes"] = frame["votes"].map(_as_votes)
    frame["budget_band"] = frame["cost_for_two"].map(
        lambda cost: budget_band(cost, low_max=low_max, med_max=med_max)
    )

    # Drop rows with no usable name.
    before = len(frame)
    frame = frame[frame["name"].astype(bool)].copy()
    logger.info("Dropped %s rows with empty name", before - len(frame))

    # Deduplicate on name + address (keep highest votes, then rating).
    frame = frame.sort_values(
        by=["votes", "rating"],
        ascending=[False, False],
        na_position="last",
    )
    before_dedup = len(frame)
    frame = frame.drop_duplicates(subset=["name", "address"], keep="first")
    logger.info("Deduplicated %s overlapping listings", before_dedup - len(frame))

    frame = frame.reset_index(drop=True)
    frame.insert(0, "id", frame.index.astype(int))

    cleaned = frame.loc[:, OUTPUT_COLUMNS].copy()
    if cleaned.empty:
        raise ValueError("All rows were dropped during cleaning; refusing to write empty cache")

    logger.info("Processed %s restaurants", len(cleaned))
    return cleaned


def build_metadata(
    restaurants: pd.DataFrame,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Build dropdown vocabularies and ingest provenance for the UI."""
    settings = settings or get_settings()

    locations = sorted(
        {loc for loc in restaurants["location"].tolist() if isinstance(loc, str) and loc}
    )
    cities = sorted(
        {
            city
            for city in restaurants["listed_in_city"].tolist()
            if isinstance(city, str) and city
        }
    )

    cuisine_vocab: set[str] = set()
    for value in restaurants["cuisines"].tolist():
        cuisine_vocab.update(cuisine_tokens(value if isinstance(value, str) else ""))

    band_counts = (
        restaurants["budget_band"]
        .fillna("unknown")
        .value_counts(dropna=False)
        .to_dict()
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "row_count": int(len(restaurants)),
        "hf_dataset_id": settings.hf_dataset_id,
        "hf_dataset_revision": settings.hf_dataset_revision,
        "budget_low_max": settings.budget_low_max,
        "budget_med_max": settings.budget_med_max,
        "locations": locations,
        "listed_in_cities": cities,
        "cuisines": sorted(cuisine_vocab),
        "budget_band_counts": {str(k): int(v) for k, v in band_counts.items()},
        "columns": list(OUTPUT_COLUMNS),
    }


def save_processed(
    restaurants: pd.DataFrame,
    metadata: dict[str, Any],
    *,
    data_path: Path | None = None,
    metadata_path: Path | None = None,
) -> tuple[Path, Path]:
    """Write Parquet + metadata JSON; create parent dirs as needed."""
    settings = get_settings()
    data_path = Path(data_path or settings.data_path)
    metadata_path = Path(metadata_path or settings.metadata_path)

    data_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    restaurants.to_parquet(data_path, index=False)
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")

    logger.info("Wrote %s (%s rows)", data_path, len(restaurants))
    logger.info("Wrote %s", metadata_path)
    return data_path, metadata_path


def prepare_dataset(
    *,
    settings: Settings | None = None,
    force: bool = False,
) -> tuple[Path, Path]:
    """Load HF data (unless cache exists), preprocess, and persist outputs.

    When ``force`` is False and both Parquet and metadata already exist,
    skip the Hugging Face download and return existing paths.
    """
    settings = settings or get_settings()
    data_path = settings.data_path
    metadata_path = settings.metadata_path

    if (
        not force
        and data_path.is_file()
        and metadata_path.is_file()
    ):
        logger.info(
            "Processed cache already exists at %s — skipping download. "
            "Pass force=True to rebuild.",
            data_path,
        )
        return data_path, metadata_path

    raw = load_raw_dataframe(settings)
    restaurants = preprocess_restaurants(
        raw,
        low_max=settings.budget_low_max,
        med_max=settings.budget_med_max,
    )
    metadata = build_metadata(restaurants, settings=settings)
    if not metadata["locations"] or not metadata["cuisines"]:
        raise ValueError(
            "Ingest produced empty location or cuisine vocabulary; check source data"
        )
    return save_processed(
        restaurants,
        metadata,
        data_path=data_path,
        metadata_path=metadata_path,
    )
