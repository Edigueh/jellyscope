"""Data store: pre-loads and caches datacubes and clump catalog offering a cache mechanism."""

from pathlib import Path

from ..config import JellyscopeConfig
from .model.clumps import ClumpCatalog
from .model.datacube import DataCube


class DataStore:
    """DataStore is a singleton that holds loaded datacubes and clump catalogs in memory."""

    _instance: "DataStore | None" = None

    def __init__(self, config: JellyscopeConfig) -> None:
        nircam_datacube: str = "nircam"
        self.config: JellyscopeConfig = config
        data: Path = config.data_dir

        self.datacubes: dict[str, DataCube] = {}
        self._load_datacube(data / config.datacube_file, nircam_datacube)
        self._load_datacube(data / config.datacube_matched_file, f"{nircam_datacube}_matched")

        if nircam_datacube not in self.datacubes:
            raise FileNotFoundError(
                f"Required datacube file not found: {data / config.datacube_file}"
            )

        # Currently using this datacube as only reference of data.
        ref_datacube: DataCube = self.datacubes[nircam_datacube]
        self.clumps = ClumpCatalog(
            data / config.clumps_properties_file,
            data / config.clumps_pixels_file,
            ref_datacube.spatial_shape,
        )

    def _load_datacube(self, path: Path, name: str) -> None:
        if path.exists():
            self.datacubes[name] = DataCube(path)

    def get_datacube(self, name: str) -> DataCube:
        if name not in self.datacubes:
            raise KeyError(
                f"Unknown datacube '{name}'. Available datacubes are: {list(self.datacubes)}"
            )
        return self.datacubes[name]

    def list_datacubes(self) -> list[str]:
        return list(self.datacubes.keys())

    def get_datacubes(self) -> dict[str, DataCube]:
        return self.datacubes

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
