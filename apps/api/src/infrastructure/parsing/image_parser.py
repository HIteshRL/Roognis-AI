from src.infrastructure.parsing.base import AbstractDocumentParser, ParsedDocument, ParsedPage


class ImageParser(AbstractDocumentParser):
    """
    Standalone image uploads (photo of a worksheet, textbook page, diagram).

    Images carry no text layer, so this parser produces a single empty page
    flagged for OCR. The VisionOCRService fills the content during the
    ingestion pipeline's enrichment step. Registering this parser is also what
    admits image extensions to the upload allow-list.
    """

    @property
    def supported_types(self) -> list[str]:
        return [
            "image/png",
            "image/jpeg",
            "image/webp",
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
        ]

    async def parse(self, file_path: str) -> ParsedDocument:
        return ParsedDocument(
            pages=[ParsedPage(page_number=1, content="", metadata={"needs_ocr": True})],
            metadata={"is_image": True},
        )
