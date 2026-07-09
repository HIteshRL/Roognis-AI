"""Unit tests for the hosted Fal video provider (no network)."""
import pytest

from src.infrastructure.videogen.fal_provider import FalVideoGenerator


class _Resp:
    def __init__(self, json_data=None, content=b""):
        self._json = json_data
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


class _FakeClient:
    """Stand-in for httpx.Client: POST returns the job JSON, GET the bytes."""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, headers=None, json=None):
        return _Resp(json_data={"video": {"url": "https://fal/out.mp4", "content_type": "video/mp4"}})

    def get(self, url):
        return _Resp(content=b"MP4_BYTES")


def test_fal_video_returns_bytes(monkeypatch):
    monkeypatch.setattr(
        "src.infrastructure.videogen.fal_provider.httpx.Client", _FakeClient
    )
    gen = FalVideoGenerator(api_key="test-key")
    result = gen.generate("Explain adding fractions", num_frames=97, fps=24)
    assert result.data == b"MP4_BYTES"
    assert result.content_type == "video/mp4"
    assert gen.provider_name == "fal"


def test_fal_video_requires_key():
    with pytest.raises(RuntimeError, match="FAL_API_KEY"):
        FalVideoGenerator(api_key="").generate("anything")


def test_fal_video_raises_without_url(monkeypatch):
    class _NoUrlClient(_FakeClient):
        def post(self, url, headers=None, json=None):
            return _Resp(json_data={"video": {}})

    monkeypatch.setattr(
        "src.infrastructure.videogen.fal_provider.httpx.Client", _NoUrlClient
    )
    with pytest.raises(RuntimeError, match="no video url"):
        FalVideoGenerator(api_key="k").generate("x")
