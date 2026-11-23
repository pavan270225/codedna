"""Edit event model and utilities."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class AttributionClass(str, Enum):
    HUMAN = "human"
    AI_GENERATED = "ai_generated"
    AI_MODIFIED = "ai_modified"
    AMBIGUOUS = "ambiguous"


@dataclass(slots=True)
class EditEvent:
    """A single text edit captured from the editor."""
    file: str
    range_start: int
    range_end: int
    text: str
    timestamp: float = field(default_factory=time.time)
    duration_ms: int = 0
    source_hint: str = ""

    @property
    def is_insertion(self) -> bool:
        return bool(self.text)

    @property
    def is_deletion(self) -> bool:
        return self.range_start != self.range_end and not self.text

    @property
    def char_count(self) -> int:
        return len(self.text)


@dataclass(slots=True)
class ClassifiedEvent:
    """An edit event with attribution classification."""
    event: EditEvent
    attribution: AttributionClass
    confidence: float
    rationale: str


def heuristic_classify(event: EditEvent) -> ClassifiedEvent:
    """Rule-based classifier for edit attribution.

    Heuristics:
    - Bulk multi-line insert in <100ms → AI_GENERATED
    - Rapid sequential small inserts with identical timing → AI_GENERATED
    - Deletion followed by insertion in same region → AI_MODIFIED
    - Slow, character-by-character → HUMAN
    - Mixed patterns → AMBIGUOUS
    """
    text = event.text
    duration = event.duration_ms
    lines = text.count("\n") + 1 if text else 0

    if duration < 100 and lines > 3 and len(text) > 200:
        return ClassifiedEvent(
            event=event,
            attribution=AttributionClass.AI_GENERATED,
            confidence=0.85,
            rationale=f"Bulk insert: {lines} lines, {len(text)} chars in {duration}ms",
        )

    if duration < 50 and len(text) > 100:
        return ClassifiedEvent(
            event=event,
            attribution=AttributionClass.AI_GENERATED,
            confidence=0.75,
            rationale=f"Fast paste-like: {len(text)} chars in {duration}ms",
        )

    if event.is_deletion and duration < 200:
        return ClassifiedEvent(
            event=event,
            attribution=AttributionClass.AI_MODIFIED,
            confidence=0.7,
            rationale=f"Quick delete+replace in {duration}ms",
        )

    if duration > 500 and len(text) < 50:
        cps = len(text) / max(duration / 1000, 0.001)
        if cps < 30:
            return ClassifiedEvent(
                event=event,
                attribution=AttributionClass.HUMAN,
                confidence=0.8,
                rationale=f"Slow typing: {cps:.1f} cps over {duration}ms",
            )

    return ClassifiedEvent(
        event=event,
        attribution=AttributionClass.AMBIGUOUS,
        confidence=0.5,
        rationale="No strong heuristic match",
    )