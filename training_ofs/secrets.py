"""Secret loaders that map Vault fields to Mandala / fsspec options."""

from __future__ import annotations

from typing import Any, Optional

from training_ofs.vault import DEFAULT_VAULT_ADDR, read_kv2_secret

DEFAULT_S3_SECRET_PATH = "secret/data/training-ofs-2026"

# Vault field names stored under secret/kv/training-ofs-2026
FIELD_S3_KEY = "s3key"
FIELD_S3_SECRET = "s3secret"
FIELD_S3_URL = "s3url"
FIELD_S3_REGION = "s3regname"


def load_s3_options_from_vault(
    *,
    secret_path: str = DEFAULT_S3_SECRET_PATH,
    token: Optional[str] = None,
    vault_addr: str = DEFAULT_VAULT_ADDR,
    verify_ssl: bool = False,
) -> dict[str, Any]:
    """Load Mandala S3 credentials from HashiCorp Vault (BMKG Maritim).

    Returns a dict suitable for ``fsspec.filesystem('s3', **options)`` /
    Mandala catalog ``options=``::

        {
            'key': ...,
            'secret': ...,
            'client_kwargs': {
                'endpoint_url': ...,
                'region_name': ...,
                'verify': False,
            },
        }
    """
    data = read_kv2_secret(
        secret_path,
        token=token,
        vault_addr=vault_addr,
    )
    missing = [
        name
        for name in (FIELD_S3_KEY, FIELD_S3_SECRET, FIELD_S3_URL, FIELD_S3_REGION)
        if name not in data
    ]
    if missing:
        raise KeyError(
            f"Vault secret {secret_path!r} missing fields: {', '.join(missing)}"
        )

    return {
        "key": data[FIELD_S3_KEY],
        "secret": data[FIELD_S3_SECRET],
        "client_kwargs": {
            "endpoint_url": data[FIELD_S3_URL],
            "region_name": data[FIELD_S3_REGION],
            "verify": verify_ssl,
        },
    }
