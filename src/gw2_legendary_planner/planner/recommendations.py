from __future__ import annotations

from pydantic import BaseModel


class Recommendation(BaseModel):
    """Placeholder for the future account progression recommendation engine."""

    title: str
    rationale: str
    priority: int = 0
