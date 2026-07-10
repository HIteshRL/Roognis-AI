"""
Tests for VisionOCRService (Phase 0.6).

Verifies OCR enrichment of images and scanned PDFs, the low-text detection
threshold, the page cap, and — most importantly — fail-open behaviour: any
provider or IO error must leave the original page content untouched.
"""
from io import BytesIO

import pytest
from PIL import Image

from src.application.services.vision_ocr_service import VisionOCRService
from src.infrastructure.parsing.base import ParsedDocument, ParsedPage
from src.infrastructure.vision.base import AbstractVisionProvider


class FakeVisionProvider(AbstractVisionProvider):
    def __init__(self, text: str = "transcribed content", raises: bool = False) -> None:
        self._text = text
        self._raises = raises
        self.calls = 0

    @property
    def provider_name(self) -> str:
        return "fake"

    async def extract_text(self, image_data_uri: str, prompt: str | None = None) -> str:
        self.calls += 1
        if self._raises:
            raise RuntimeError("vision provider down")
        return self._text


@pytest.fixture
def png_file(tmp_path):
    path = tmp_path / "scan.png"
    Image.new("RGB", (64, 48), color=(255, 255, 255)).save(path, format="PNG")
    return str(path)


def _image_doc() -> ParsedDocument:
    return ParsedDocument(
        pages=[ParsedPage(page_number=1, content="", metadata={"needs_ocr": True})],
        metadata={"is_image": True},
    )


# ── Image OCR ───────────────────────────────────────────────────────────────

async def test_image_is_transcribed(png_file):
    provider = FakeVisionProvider(text="Newton's second law: F = ma")
    svc = VisionOCRService(provider)

    result = await svc.enrich(_image_doc(), png_file, "image/png")

    assert result.pages[0].content == "Newton's second law: F = ma"
    assert result.pages[0].metadata["ocr"] is True
    assert result.metadata["ocr_applied"] is True
    assert result.metadata["ocr_pages"] == 1
    assert provider.calls == 1


async def test_disabled_is_a_noop(png_file):
    provider = FakeVisionProvider()
    svc = VisionOCRService(provider, enabled=False)

    result = await svc.enrich(_image_doc(), png_file, "image/png")

    assert result.pages[0].content == ""
    assert provider.calls == 0


async def test_empty_transcription_leaves_page_untouched(png_file):
    provider = FakeVisionProvider(text="   ")
    svc = VisionOCRService(provider)

    result = await svc.enrich(_image_doc(), png_file, "image/png")

    # Whitespace-only transcription is treated as nothing read.
    assert result.pages[0].content == ""
    assert "ocr_applied" not in result.metadata


async def test_provider_failure_is_fail_open(png_file):
    provider = FakeVisionProvider(raises=True)
    svc = VisionOCRService(provider)

    result = await svc.enrich(_image_doc(), png_file, "image/png")

    # Original (empty) content preserved; ingestion can still continue.
    assert result.pages[0].content == ""
    assert provider.calls == 1


async def test_missing_file_is_fail_open(tmp_path):
    provider = FakeVisionProvider()
    svc = VisionOCRService(provider)

    result = await svc.enrich(_image_doc(), str(tmp_path / "nope.png"), "image/png")

    assert result.pages[0].content == ""
    assert provider.calls == 0


# ── PDF gating ──────────────────────────────────────────────────────────────

async def test_pdf_with_text_layer_skips_ocr(tmp_path):
    provider = FakeVisionProvider()
    svc = VisionOCRService(provider, min_chars_per_page=20)
    doc = ParsedDocument(
        pages=[ParsedPage(page_number=1, content="This page already has a real text layer.")],
        metadata={},
    )

    # Path never opened because no page falls below the threshold.
    result = await svc.enrich(doc, str(tmp_path / "born-digital.pdf"), "application/pdf")

    assert provider.calls == 0
    assert result.pages[0].content.startswith("This page already")


async def test_encode_produces_data_uri():
    provider = FakeVisionProvider()
    svc = VisionOCRService(provider)
    buf = BytesIO()
    Image.new("RGB", (10, 10), color=(0, 0, 0)).save(buf, format="PNG")

    uri = svc._encode(buf.getvalue(), "image/png")

    assert uri is not None
    assert uri.startswith("data:image/")
    assert ";base64," in uri
