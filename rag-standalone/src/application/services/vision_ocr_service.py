"""
Phase 0.6: Vision OCR Service.

Turns scanned PDFs and uploaded images into searchable text so they flow
through the existing chunk -> embed -> index pipeline unchanged.

Insertion point: called by IngestionPipeline immediately after parsing and
before chunking. It inspects the ParsedDocument, finds pages with little or no
extractable text, transcribes their images via a vision model, and writes the
result back into the page content. Pages that already have text are left alone.

Fail-open everywhere: OCR is an enrichment, never a correctness dependency. A
failure to read, encode, or transcribe any page logs and leaves that page's
original content intact so ingestion still completes.
"""
import base64
import os

import structlog

from src.infrastructure.parsing.base import ParsedDocument, ParsedPage
from src.infrastructure.vision.base import AbstractVisionProvider

logger = structlog.get_logger(__name__)

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
_PDF_EXTS = {".pdf"}
_EXT_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


class VisionOCRService:
    def __init__(
        self,
        vision_provider: AbstractVisionProvider,
        enabled: bool = True,
        min_chars_per_page: int = 20,
        max_pages: int = 40,
        max_image_dimension: int = 1536,
        image_format: str = "jpeg",
    ) -> None:
        self._vision = vision_provider
        self._enabled = enabled
        self._min_chars = min_chars_per_page
        self._max_pages = max_pages
        self._max_dim = max_image_dimension
        self._image_format = image_format

    async def enrich(
        self, parsed: ParsedDocument, storage_path: str, file_type: str | None = None
    ) -> ParsedDocument:
        """Return a ParsedDocument with low-text pages transcribed via OCR.

        Never raises — returns the original document on any failure.
        """
        if not self._enabled:
            return parsed

        try:
            ext = os.path.splitext(storage_path)[1].lower()
            if parsed.metadata.get("is_image") or ext in _IMAGE_EXTS:
                return await self._ocr_image_file(parsed, storage_path, ext)
            if ext in _PDF_EXTS:
                return await self._ocr_pdf(parsed, storage_path)
        except Exception as exc:
            logger.warning("ocr_enrich_failed", path=storage_path, error=str(exc))
        return parsed

    # ── Image files ───────────────────────────────────────────────────────────

    async def _ocr_image_file(
        self, parsed: ParsedDocument, storage_path: str, ext: str
    ) -> ParsedDocument:
        try:
            with open(storage_path, "rb") as fh:
                raw = fh.read()
        except OSError as exc:
            logger.warning("ocr_image_read_failed", path=storage_path, error=str(exc))
            return parsed

        data_uri = self._encode(raw, _EXT_MIME.get(ext, "image/jpeg"))
        if not data_uri:
            return parsed

        text = await self._transcribe(data_uri, page=1)
        if not text:
            return parsed

        return ParsedDocument(
            pages=[ParsedPage(page_number=1, content=text, metadata={"ocr": True})],
            metadata={**parsed.metadata, "ocr_applied": True, "ocr_pages": 1},
        )

    # ── Scanned PDFs ────────────────────────────────────────────────────────────

    async def _ocr_pdf(self, parsed: ParsedDocument, storage_path: str) -> ParsedDocument:
        low_text = [p for p in parsed.pages if len(p.content.strip()) < self._min_chars]
        if not low_text:
            return parsed

        try:
            from pypdf import PdfReader

            reader = PdfReader(storage_path)
        except Exception as exc:
            logger.warning("ocr_pdf_open_failed", path=storage_path, error=str(exc))
            return parsed

        ocr_count = 0
        for page in parsed.pages:
            if len(page.content.strip()) >= self._min_chars:
                continue
            if ocr_count >= self._max_pages:
                logger.info("ocr_page_cap_reached", cap=self._max_pages, path=storage_path)
                break

            idx = page.page_number - 1
            if idx < 0 or idx >= len(reader.pages):
                continue

            images = self._pdf_page_images(reader, idx)
            if not images:
                continue

            texts: list[str] = []
            for raw in images:
                data_uri = self._encode(raw, "image/png")
                if not data_uri:
                    continue
                transcribed = await self._transcribe(data_uri, page=page.page_number)
                if transcribed:
                    texts.append(transcribed)

            if texts:
                page.content = "\n\n".join(texts)
                page.metadata = {**page.metadata, "ocr": True}
                ocr_count += 1

        if ocr_count:
            parsed.metadata = {**parsed.metadata, "ocr_applied": True, "ocr_pages": ocr_count}
            logger.info("ocr_pdf_complete", path=storage_path, pages_ocred=ocr_count)
        return parsed

    @staticmethod
    def _pdf_page_images(reader, page_index: int) -> list[bytes]:
        try:
            page = reader.pages[page_index]
            out: list[bytes] = []
            for img in page.images:
                try:
                    out.append(img.data)
                except Exception:
                    continue
            return out
        except Exception:
            return []

    # ── Transcription + encoding ────────────────────────────────────────────────

    async def _transcribe(self, data_uri: str, page: int) -> str:
        try:
            text = await self._vision.extract_text(data_uri)
        except Exception as exc:
            logger.warning("ocr_transcribe_failed", page=page, error=str(exc))
            return ""
        # A whitespace-only transcription means nothing legible was read; treat
        # it as empty so callers leave the page's original content untouched.
        return text.strip() if text else ""

    def _encode(self, image_bytes: bytes, fallback_mime: str) -> str | None:
        """Downscale + re-encode via Pillow; fall back to raw base64 on failure."""
        encoded = self._downscale_encode(image_bytes)
        if encoded:
            return encoded
        try:
            b64 = base64.b64encode(image_bytes).decode()
            return f"data:{fallback_mime};base64,{b64}"
        except Exception as exc:
            logger.warning("ocr_encode_failed", error=str(exc))
            return None

    def _downscale_encode(self, image_bytes: bytes) -> str | None:
        try:
            from io import BytesIO

            from PIL import Image

            img = Image.open(BytesIO(image_bytes))
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            if max(img.size) > self._max_dim:
                img.thumbnail((self._max_dim, self._max_dim))

            fmt = "JPEG" if self._image_format == "jpeg" else "PNG"
            mime = "image/jpeg" if fmt == "JPEG" else "image/png"
            buf = BytesIO()
            if fmt == "JPEG" and img.mode != "RGB":
                img = img.convert("RGB")
            img.save(buf, format=fmt, quality=85)
            b64 = base64.b64encode(buf.getvalue()).decode()
            return f"data:{mime};base64,{b64}"
        except Exception as exc:
            logger.debug("ocr_downscale_skipped", error=str(exc))
            return None
