"""Tests for the multi-dataset DataStore."""

from pathlib import Path

import pytest

from jellyscope.config import JellyscopeConfig
from jellyscope.data.data_store import DEFAULT_DATASET, NIRCAM, NIRCAM_MATCHED, DataStore


@pytest.fixture(autouse=True)
def _reset_store():
    DataStore.reset()
    yield
    DataStore.reset()


def test_discovers_subdirectory_datasets(config):
    store = DataStore.get(config)
    names = store.list_datasets()
    assert "A2744_F1228" in names
    assert "A2744_HLS001428_302334" in names
    assert "jellyfish_5" in names
    assert store.default_dataset in names


def test_dataset_with_only_matched_cube_loads(config):
    store = DataStore.get(config)
    ds = store.get_dataset("A2744_HLS001428_302334")
    assert NIRCAM_MATCHED in ds.datacubes
    assert NIRCAM not in ds.datacubes
    assert ds.clumps is not None


def test_dataset_with_both_cubes_loads(config):
    store = DataStore.get(config)
    ds = store.get_dataset("A2744_F1228")
    assert NIRCAM in ds.datacubes
    assert NIRCAM_MATCHED in ds.datacubes


def test_unknown_dataset_raises(config):
    store = DataStore.get(config)
    with pytest.raises(KeyError):
        store.get_dataset("nope")


def test_empty_data_dir_raises(tmp_path: Path):
    cfg = JellyscopeConfig(data_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        DataStore(cfg)


def test_missing_data_dir_raises(tmp_path: Path):
    cfg = JellyscopeConfig(data_dir=tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        DataStore(cfg)


def test_subdir_missing_csvs_skipped(tmp_path: Path):
    # Subdir with CSVs but no cube -> skipped (cube required first), no datasets -> error.
    sub = tmp_path / "broken"
    sub.mkdir()
    (sub / "clumps_properties.csv").write_text("")
    (sub / "clumps_pixels.csv").write_text("")
    cfg = JellyscopeConfig(data_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        DataStore(cfg)


def test_flat_layout_fallback_uses_default_name(tmp_path: Path, monkeypatch):
    # Build a tmp dir mirroring the project's flat data dir by symlinking
    # the necessary files from the real data dir's A2744_F1228 subdir.
    src = Path("data/A2744_F1228")
    if not src.exists():
        pytest.skip("real dataset not available")
    for fname in [
        "cut_datacube_nircam.fits",
        "cut_datacube_nircam_matched.fits",
        "clumps_properties.csv",
        "clumps_pixels.csv",
    ]:
        (tmp_path / fname).symlink_to((src / fname).resolve())

    cfg = JellyscopeConfig(data_dir=tmp_path)
    store = DataStore(cfg)
    assert store.list_datasets() == [DEFAULT_DATASET]
