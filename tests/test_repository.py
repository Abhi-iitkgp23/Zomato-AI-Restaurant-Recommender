"""Repository helpers against a temporary processed cache."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from zomato_rec.data.ingest import build_metadata, preprocess_restaurants, save_processed
from zomato_rec.data.repository import (
    DataNotPreparedError,
    clear_cache,
    list_cuisines,
    list_locations,
    load_metadata,
    load_restaurants,
)


@pytest.fixture
def processed_dir(tmp_path: Path, monkeypatch):
    raw = pd.DataFrame(
        [
            {
                "name": "Cafe A",
                "location": "Koramangala",
                "listed_in(city)": "Koramangala",
                "address": "1 A St",
                "url": "https://example.com/a",
                "cuisines": "Cafe, Italian",
                "rate": "4.2/5",
                "votes": 100,
                "approx_cost(for two people)": "500",
                "rest_type": "Cafe",
                "dish_liked": "Pasta",
                "online_order": "Yes",
                "book_table": "No",
            }
        ]
    )
    cleaned = preprocess_restaurants(raw)
    meta = build_metadata(cleaned)
    data_path = tmp_path / "restaurants.parquet"
    metadata_path = tmp_path / "metadata.json"
    save_processed(cleaned, meta, data_path=data_path, metadata_path=metadata_path)

    clear_cache()
    monkeypatch.setenv("DATA_PATH", str(data_path))
    monkeypatch.setenv("METADATA_PATH", str(metadata_path))
    from zomato_rec.config import get_settings

    get_settings.cache_clear()
    yield data_path, metadata_path
    clear_cache()
    get_settings.cache_clear()


def test_load_restaurants_and_vocab(processed_dir):
    frame = load_restaurants()
    assert len(frame) == 1
    assert list_locations() == ["Koramangala"]
    assert "italian" in list_cuisines()
    assert "cafe" in list_cuisines()
    meta = load_metadata()
    assert meta["row_count"] == 1


def test_missing_parquet_raises(tmp_path, monkeypatch):
    missing = tmp_path / "missing.parquet"
    monkeypatch.setenv("DATA_PATH", str(missing))
    monkeypatch.setenv("METADATA_PATH", str(tmp_path / "missing.json"))
    from zomato_rec.config import get_settings

    get_settings.cache_clear()
    clear_cache()
    with pytest.raises(DataNotPreparedError, match="prepare_dataset"):
        load_restaurants()
