"""
Optional bridge: forward demo evidence to apps/api's real Learner Intelligence engine.

Default OFF and fail-open. Set both env vars to enable:
  ROOGNIS_BRIDGE_URL    e.g. http://localhost:8000
  ROOGNIS_BRIDGE_TOKEN  must match apps/api's BRIDGE_INGEST_TOKEN

Uses only the stdlib (urllib) so the self-contained demo gains no dependency.
Any failure is swallowed — the demo must never break because the bridge is down.
"""
import json
import os
import urllib.request

_PATH = "/api/v1/learner/evidence/ingest"


def _config() -> tuple[str, str]:
    return os.environ.get("ROOGNIS_BRIDGE_URL", "").rstrip("/"), os.environ.get("ROOGNIS_BRIDGE_TOKEN", "")


def enabled() -> bool:
    url, token = _config()
    return bool(url and token)


def forward_evidence(payload: dict) -> None:
    """Best-effort POST of one evidence event. No-op unless configured; never raises."""
    url, token = _config()
    if not (url and token):
        return
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url + _PATH, data=data, method="POST",
            headers={"Content-Type": "application/json", "X-Bridge-Token": token},
        )
        urllib.request.urlopen(req, timeout=4).read()  # noqa: S310 (fixed internal host)
    except Exception:
        pass
