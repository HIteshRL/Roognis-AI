import structlog
from pypdf import PdfReader

from src.infrastructure.parsing.base import AbstractDocumentParser, ParsedDocument, ParsedPage

logger = structlog.get_logger(__name__)


class PDFParser(AbstractDocumentParser):
    @property
    def supported_types(self) -> list[str]:
        return ["application/pdf", ".pdf"]

    async def parse(self, file_path: str) -> ParsedDocument:
        try:
            reader = PdfReader(file_path)
            pages: list[ParsedPage] = []
            for i, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                pages.append(ParsedPage(page_number=i, content=text.strip()))
            metadata = {}
            if reader.metadata:
                metadata = {
                    "title": reader.metadata.title,
                    "author": reader.metadata.author,
                    "subject": reader.metadata.subject,
                }
            return ParsedDocument(pages=pages, metadata=metadata)
        except Exception as e:
            logger.error("pdf_parse_error", path=file_path, error=str(e))
            raise
