"""Data store: discovers and caches datasets (datacubes + clump catalogs)."""

import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from jellyscope.config import JellyscopeConfig
from jellyscope.data.model.clumps import ClumpCatalog
from jellyscope.data.model.datacube import DataCube

logger = logging.getLogger(__name__)

NIRCAM = "nircam"
NIRCAM_MATCHED = "nircam_matched"
DEFAULT_DATASET = "default"


class Dataset(BaseModel):
    """A self-contained dataset: one or more datacubes + a clump catalog."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    datacubes: dict[str, DataCube] = {}
    clumps: ClumpCatalog | None = None

    def get_datacube(self, name: str) -> DataCube:
        if name not in self.datacubes:
            raise KeyError(
                f"Unknown datacube '{name}' in dataset '{self.name}'. "
                f"Available: {list(self.datacubes)}"
            )
        return self.datacubes[name]

    def list_datacubes(self) -> list[str]:
        return list(self.datacubes.keys())


class DataStore:
    """Singleton holding all discovered datasets in memory."""

    _instance: "DataStore | None" = None

    def __init__(self, config: JellyscopeConfig) -> None:
        self.config: JellyscopeConfig = config
        self.datasets: dict[str, Dataset] = {}

        data_dir: Path = config.data_dir
        if not data_dir.exists():
            raise FileNotFoundError(f"data_dir does not exist: {data_dir}")

        # Discover subdirectory-based datasets first.
        for sub in sorted(p for p in data_dir.iterdir() if p.is_dir()):
            ds = self._try_load_dataset(sub, name=sub.name)
            if ds is not None:
                self.datasets[ds.name] = ds

        # Backward-compat: flat layout — root data_dir as a single dataset.
        if not self.datasets:
            ds = self._try_load_dataset(data_dir, name=DEFAULT_DATASET)
            if ds is not None:
                self.datasets[ds.name] = ds

        if not self.datasets:
            raise FileNotFoundError(
                f"No valid datasets found under {data_dir}. "
                f"Each dataset needs the matched FITS cube and both clump CSVs."
            )

        self.default_dataset: str = next(iter(self.datasets))

    def _try_load_dataset(self, root: Path, name: str) -> Dataset | None:
        """Try to build a Dataset from `root`. Returns None if requirements unmet."""
        cfg = self.config
        ds = Dataset(name=name)

        base_path = root / cfg.datacube_file
        matched_path = root / cfg.datacube_matched_file
        if base_path.exists():
            ds.datacubes[NIRCAM] = DataCube(base_path)
        if matched_path.exists():
            ds.datacubes[NIRCAM_MATCHED] = DataCube(matched_path)

        if not ds.datacubes:
            logger.warning("Skipping '%s': no datacube files found", root)
            return None

        props_path = root / cfg.clumps_properties_file
        pixels_path = root / cfg.clumps_pixels_file
        if not props_path.exists() or not pixels_path.exists():
            logger.warning("Skipping '%s': missing clump CSVs", root)
            return None

        # Use the base nircam cube as reference if present, otherwise matched.
        ref = ds.datacubes.get(NIRCAM) or ds.datacubes[NIRCAM_MATCHED]
        ds.clumps = ClumpCatalog(props_path, pixels_path, ref.spatial_shape)

        # Attach RA/Dec to clump centroids when the reference WCS is celestial.
        # Without this, ra_deg / dec_deg stay None and the separations endpoint
        # returns 422; the rest of the app keeps working.
        if ref.wcs is not None and ref.wcs.has_celestial:
            ds.clumps.attach_skycoords(ref.wcs)
        else:
            logger.warning("Dataset '%s': no celestial WCS — RA/Dec disabled", name)

        return ds

    # Dataset access.
    def list_datasets(self) -> list[str]:
        return list(self.datasets.keys())

    def get_dataset(self, name: str) -> Dataset:
        if name not in self.datasets:
            raise KeyError(f"Unknown dataset '{name}'. Available: {list(self.datasets)}")
        return self.datasets[name]

    @classmethod
    def get(cls, config: JellyscopeConfig | None = None) -> "DataStore":
        """Return the singleton instance."""
        if cls._instance is None:
            if config is None:
                config = JellyscopeConfig()
            cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance."""
        cls._instance = None
