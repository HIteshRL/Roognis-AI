import os

from src.infrastructure.parsing.base import AbstractDocumentParser
from src.infrastructure.parsing.docx_parser import DocxParser
from src.infrastructure.parsing.pdf_parser import PDFParser
from src.infrastructure.parsing.pptx_parser import PptxParser
from src.infrastructure.parsing.text_parser import HtmlParser, MarkdownParser, TextParser

_PARSERS: list[AbstractDocumentParser] = [
    PDFParser(),
    DocxParser(),
    PptxParser(),
    TextParser(),
    MarkdownParser(),
    HtmlParser(),
]

_EXT_MAP: dict[str, AbstractDocumentParser] = {}
for _p in _PARSERS:
    for _t in _p.supported_types:
        _EXT_MAP[_t.lower()] = _p


def get_parser(file_path: str, content_type: str | None = None) -> AbstractDocumentParser:
    ext = os.path.splitext(file_path)[1].lower()
    if ext in _EXT_MAP:
        return _EXT_MAP[ext]
    if content_type and content_type.lower() in _EXT_MAP:
        return _EXT_MAP[content_type.lower()]
    raise ValueError(f"Unsupported file type: ext={ext!r}, content_type={content_type!r}")


SUPPORTED_EXTENSIONS: list[str] = [
    k for k in _EXT_MAP if k.startswith(".")
]

SUPPORTED_CONTENT_TYPES: list[str] = [
    k for k in _EXT_MAP if not k.startswith(".")
]
