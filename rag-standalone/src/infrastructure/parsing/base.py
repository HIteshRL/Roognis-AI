from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParsedPage:
    page_number: int
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ParsedDocument:
    pages: list[ParsedPage]
    metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.content for p in self.pages if p.content.strip())

    @property
    def total_pages(self) -> int:
        return len(self.pages)


class AbstractDocumentParser(ABC):
    @abstractmethod
    async def parse(self, file_path: str) -> ParsedDocument: ...

    @property
    @abstractmethod
    def supported_types(self) -> list[str]: ...
