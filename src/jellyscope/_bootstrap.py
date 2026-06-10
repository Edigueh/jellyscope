"""Bootstrap helpers for runtime data provisioning.

When deployed to environments without a pre-mounted data volume (such as
Hugging Face Spaces), the application downloads its dataset from the
Hugging Face Hub on first start.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DATA_REPO = "EAT-Prototypes/scoped_jellyfishes"
DATA_REPO_ENV_VAR = "JELLYSCOPE_DATA_REPO"


def ensure_data(target: Path) -> None:
    """Populate ``target`` from the Hugging Face dataset if it is empty.

    No-op when ``target`` already contains files. The dataset repo can be
    overridden via the ``JELLYSCOPE_DATA_REPO`` environment variable.
    """
    target = Path(target)
    if target.exists() and any(target.iterdir()):
        return

    target.mkdir(parents=True, exist_ok=True)
    repo_id = os.environ.get(DATA_REPO_ENV_VAR, DEFAULT_DATA_REPO)

    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        local_dir=str(target),
    )
