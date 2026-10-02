"""Token loading for the API-gated sources.

Tokens are read from a gitignored `.env` at the repo root, or from the
process environment. Never commit them.

    ESIOS_TOKEN=...
    ENTSOE_TOKEN=...

How to obtain them (both free, both require a human):

* **ESIOS** -- request a personal token with the form at
  https://www.esios.ree.es/es/token (REE's route since 2026-09-18; its desk
  answers email requests by pointing there). It arrives by email and goes in the ``x-api-key``
  header (checked 2026-10-02). It is personal, and REE asks that data already
  downloaded is not requested again.
* **ENTSO-E** -- register at https://transparency.entsoe.eu, then email
  ``transparency@entsoe.eu`` from the registered address asking for API
  access. The token then appears in your account settings.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
ENV = REPO / ".env"


def load_env() -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file, ignoring comments and blanks."""
    out: dict[str, str] = {}
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def get_token(name: str) -> str | None:
    """Environment wins over .env, so a shell export can override the file."""
    return os.environ.get(name) or load_env().get(name)


def require_token(name: str) -> str:
    tok = get_token(name)
    if not tok:
        raise SystemExit(
            f"\nMissing {name}.\n\n"
            f"Add it to {ENV} as:\n    {name}=your_token_here\n\n"
            f"{__doc__.split('How to obtain them')[1].strip()}\n"
        )
    return tok
