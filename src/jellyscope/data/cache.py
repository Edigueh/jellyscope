"""Data store: pre-loads and caches datacubes and clump catalog."""

from pathlib import Path

from ..config import JellyscopeConfig
from .fits_handler import DataCube
from .clumps import ClumpCatalog


class DataStore:
    """Holds loaded datacubes and clump catalog in memory.

    For small datasets this loads everything eagerly. Can be extended
    with lazy-loading / LRU eviction for larger collections.
    """

    _instance: "DataStore | None" = None

    def __init__(self, config: JellyscopeConfig) -> None:
        self.config = config
        data = config.data_dir

        self.datacubes: dict[str, DataCube] = {}
        self._load_datacube(data / config.datacube_file, "nircam")
        self._load_datacube(data / config.datacube_matched_file, "nircam_matched")

        ref_dc = self.datacubes["nircam"]
        self.clumps = ClumpCatalog(
            data / config.clumps_properties_file,
            data / config.clumps_pixels_file,
            ref_dc.spatial_shape,
        )

    def _load_datacube(self, path: Path, name: str) -> None:
        if path.exists():
            self.datacubes[name] = DataCube(path)

    def get_datacube(self, name: str) -> DataCube:
        if name not in self.datacubes:
            raise KeyError(f"Unknown datacube '{name}'. Available: {list(self.datacubes)}")
        return self.datacubes[name]

    def list_datacubes(self) -> list[str]:
        return list(self.datacubes.keys())

    @classmethod
    def get(cls, config: JellyscopeConfig | None = None) -> "DataStore":
        if cls._instance is None:
            if config is None:
                config = JellyscopeConfig()
            cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (useful for testing)."""
        cls._instance = None
