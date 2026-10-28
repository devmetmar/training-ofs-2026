"""Minimal .env loader and portable project-root discovery.

No absolute home paths (e.g. ``/home/<user>/...``) — works for any
Mandalahub account / per-participant workdir that contains this repo.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Mapping, MutableMapping, Optional, Sequence, Union


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
        # Treat missing OR empty existing values as unset so a blank
        # VAULT_TOKEN=/USEROPENDAP= in the kernel env does not block .env.
        if override or not env.get(key):
            env[key] = value
    return loaded


def _looks_like_project_root(path: Path) -> bool:
    return (path / "training_ofs").is_dir() and (
        (path / "opendap-tutorial.ipynb").is_file()
        or (path / "mandala-tutorial.ipynb").is_file()
        or (path / "README.md").is_file()
    )


def find_project_root(
    start: Optional[Union[str, Path]] = None,
    *,
    max_up: int = 8,
) -> Path:
    """Locate the training repo root from ``start`` (default: cwd).

    Walks parent directories until a folder containing ``training_ofs/`` is found.
    Also checks directories already on ``sys.path`` (useful when the package is
    imported from another workdir copy).
    """
    starts: list[Path] = []
    if start is not None:
        starts.append(Path(start).expanduser().resolve())
    starts.append(Path.cwd().resolve())

    # Package install / editable location: .../training_ofs/envfile.py → parents[1]
    starts.append(Path(__file__).resolve().parents[1])

    for entry in list(sys.path):
        if not entry or entry == ".":
            continue
        try:
            starts.append(Path(entry).resolve())
        except OSError:
            continue

    seen: set[Path] = set()
    for base in starts:
        cur = base if base.is_dir() else base.parent
        for _ in range(max_up + 1):
            if cur in seen:
                break
            seen.add(cur)
            if _looks_like_project_root(cur):
                return cur
            if cur.parent == cur:
                break
            cur = cur.parent

    raise FileNotFoundError(
        "Could not find the training-ofs project root (folder with "
        "'training_ofs/'). Open the notebook from your workdir copy of the "
        "repo, or set the working directory to that folder."
    )


def find_env_file(
    start: Optional[Union[str, Path]] = None,
    *,
    filename: str = ".env",
) -> Path:
    """Return ``<project_root>/.env`` (may not exist yet)."""
    return find_project_root(start) / filename


def load_project_env(
    start: Optional[Union[str, Path]] = None,
    *,
    filename: str = ".env",
    environ: Optional[MutableMapping[str, str]] = None,
    override: bool = False,
    required_keys: Optional[Sequence[str]] = None,
) -> Path:
    """Load ``.env`` from the discovered project root.

    Returns the path that was used. Raises ``FileNotFoundError`` if the file
    is missing, or ``KeyError`` if ``required_keys`` are not set after load
    (checks environment, so pre-exported vars still count).
    """
    root = find_project_root(start)
    env_path = root / filename
    if env_path.is_file():
        load_env_file(env_path, environ=environ, override=override)
    elif required_keys:
        # Still allow purely environment-based secrets, but surface a clear hint.
        env = environ if environ is not None else os.environ
        missing = [k for k in required_keys if not env.get(k)]
        if missing:
            raise FileNotFoundError(
                f"Missing {env_path} and environment keys: {', '.join(missing)}. "
                f"Create {filename} in your workdir project root ({root}) or export "
                "the variables before running the notebook."
            )

    if required_keys:
        env = environ if environ is not None else os.environ
        missing = [k for k in required_keys if not env.get(k)]
        if missing:
            raise KeyError(
                f"Required secrets not set: {', '.join(missing)}. "
                f"Add them to {env_path} (per-workdir) or export them."
            )
    return env_path
