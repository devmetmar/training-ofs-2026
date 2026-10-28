"""Minimal .env loader (no python-dotenv dependency)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, MutableMapping, Optional, Union


def load_env_file(
    path: Union[str, Path] = ".env",
    *,
    environ: Optional[MutableMapping[str, str]] = None,
    override: bool = False,
) -> Mapping[str, str]:
    """Parse KEY=VALUE lines into ``environ`` (default: ``os.environ``).

    Quotes around values are stripped. Lines starting with ``#`` are ignored.
    Existing variables are kept unless ``override=True``.
    """
    env = environ if environ is not None else os.environ
    loaded: dict[str, str] = {}
    p = Path(path)
    if not p.is_file():
        return loaded

    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        loaded[key] = value
        if override or key not in env:
            env[key] = value
    return loaded
