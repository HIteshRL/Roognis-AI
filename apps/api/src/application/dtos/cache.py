from pydantic import BaseModel


class FaqResponse(BaseModel):
    id: str
    question: str
    answer: str
    subject: str | None
    grade: str | None
    hit_count: int


class CacheStatsResponse(BaseModel):
    redis_available: bool
    faq_entries: int
    default_ttl_seconds: int
    hot_ttl_seconds: int
    hot_threshold: int
    faq_promote_threshold: int
