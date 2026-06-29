import aiofiles
import markdown
from bs4 import BeautifulSoup

from src.infrastructure.parsing.base import AbstractDocumentParser, ParsedDocument, ParsedPage


class TextParser(AbstractDocumentParser):
    @property
    def supported_types(self) -> list[str]:
        return ["text/plain", ".txt", "text/csv", ".csv"]

    async def parse(self, file_path: str) -> ParsedDocument:
        async with aiofiles.open(file_path, encoding="utf-8", errors="replace") as f:
            content = await f.read()
        return ParsedDocument(pages=[ParsedPage(page_number=1, content=content.strip())])


class MarkdownParser(AbstractDocumentParser):
    @property
    def supported_types(self) -> list[str]:
        return ["text/markdown", ".md", ".markdown"]

    async def parse(self, file_path: str) -> ParsedDocument:
        async with aiofiles.open(file_path, encoding="utf-8", errors="replace") as f:
            raw = await f.read()
        html = markdown.markdown(raw)
        text = BeautifulSoup(html, "html.parser").get_text(separator="\n").strip()
        return ParsedDocument(pages=[ParsedPage(page_number=1, content=text)])


class HtmlParser(AbstractDocumentParser):
    @property
    def supported_types(self) -> list[str]:
        return ["text/html", ".html", ".htm"]

    async def parse(self, file_path: str) -> ParsedDocument:
        async with aiofiles.open(file_path, encoding="utf-8", errors="replace") as f:
            raw = await f.read()
        text = BeautifulSoup(raw, "html.parser").get_text(separator="\n").strip()
        return ParsedDocument(pages=[ParsedPage(page_number=1, content=text)])
