import hashlib
import json
import re

_PUNCT_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")


class QueryNormalizer:
    """Stateless: collapse phrasing variance so equivalent questions share a key."""

    @staticmethod
    def normalize(query: str) -> str:
        text = query.strip().lower()
        text = _PUNCT_RE.sub(" ", text)
        return _WHITESPACE_RE.sub(" ", text).strip()

    @classmethod
    def semantic_hash(cls, query: str, scope: dict | None, ns_version: int = 1) -> str:
        normalized = cls.normalize(query)
        scope_json = json.dumps(scope or {}, sort_keys=True)
        raw = f"{normalized}|{scope_json}|v{ns_version}"
        return hashlib.sha256(raw.encode()).hexdigest()
