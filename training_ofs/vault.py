"""HashiCorp Vault helpers for BMKG Maritim."""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional

import requests

DEFAULT_VAULT_ADDR = "https://api-maritim.bmkg.go.id/vault"
DEFAULT_USER_AGENT = "training-ofs-2026/1.0"


def get_vault_token(token: Optional[str] = None) -> str:
    """Resolve a Vault token from the argument or ``VAULT_TOKEN`` env var."""
    resolved = token or os.environ.get("VAULT_TOKEN")
    if not resolved:
        raise ValueError(
            "Vault token is required. Pass token=... or set VAULT_TOKEN."
        )
    return resolved


def read_kv2_secret(
    secret_path: str,
    *,
    token: Optional[str] = None,
    vault_addr: str = DEFAULT_VAULT_ADDR,
    timeout: float = 30.0,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict[str, Any]:
    """Read a KV v2 secret and return its ``data`` map.

    Parameters
    ----------
    secret_path:
        API path including the ``data/`` segment, e.g.
        ``secret/data/training-ofs-2026``.
    token:
        Vault token. Defaults to the ``VAULT_TOKEN`` environment variable.
    vault_addr:
        Vault base URL (no trailing ``/v1``).
    """
    url = f"{vault_addr.rstrip('/')}/v1/{secret_path.lstrip('/')}"
    # Cloudflare in front of Vault rejects the default requests User-Agent.
    headers = {
        "X-Vault-Token": get_vault_token(token),
        "User-Agent": user_agent,
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    payload: Mapping[str, Any] = resp.json()
    try:
        return dict(payload["data"]["data"])
    except (KeyError, TypeError) as exc:
        raise ValueError(
            f"Unexpected Vault response for {secret_path!r}: missing data.data"
        ) from exc
