"""Display payload for the clump properties panel.

The frontend renders these as a generic two-column table. Keeping an ordered
``entries`` list (instead of a flat dict) preserves row order across JSON
serialization and avoids stringly-typed dict keys.
"""

from pydantic import BaseModel, ConfigDict


class DisplayEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    value: str


class ClumpDetailDisplay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[DisplayEntry]
