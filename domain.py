"""Minimal domain layer for the Learning Orchestrator."""
from pydantic import BaseModel


class ConceptExtractionResult(BaseModel):
    primary_concept: str
    secondary_concepts: list[str] = []
    skills: list[str] = []
    bloom_level: str = "Understand"
    difficulty: str = "medium"
    misconceptions: list[str] = []
