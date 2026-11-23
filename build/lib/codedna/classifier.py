"""Heuristic edit classifier for AI vs human attribution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Attribution, AttributionLabel, ProvenanceRegion


@dataclass(slots=True)
class EditEvent:
    """Raw edit event from the editor."""

    file: Path
    start_line: int
    end_line: int
    inserted_text: str
    deleted_text: str
    timestamp: float  # epoch ms
    duration_ms: int  # time since last event
    source_hint: str | None = None  # "copilot", "cursor", "bulk-paste", etc.


@dataclass(slots=True)
class ClassifierConfig:
    """Tunable thresholds for the classifier."""

    # Bulk insert threshold: lines inserted in a single event
    bulk_line_threshold: int = 10
    # Speed threshold: chars per ms suggesting non-human typing
    speed_threshold_cpm: float = 50.0  # chars per ms
    # Minimum confidence to assign non-ambiguous label
    min_confidence: float = 0.6
    # Window for grouping rapid events (ms)
    grouping_window_ms: int = 500


class Classifier:
    """Rule-based classifier for edit attribution."""

    def __init__(self, config: ClassifierConfig | None = None):
        self.config = config or ClassifierConfig()

    def classify(self, event: EditEvent) -> Attribution:
        """Classify a single edit event."""
        label, confidence = self._score_event(event)
        return Attribution(
            file=event.file,
            start_line=event.start_line,
            end_line=event.end_line,
            label=label,
            confidence=confidence,
            source_hint=event.source_hint,
            metadata={
                "inserted_chars": len(event.inserted_text),
                "deleted_chars": len(event.deleted_text),
                "duration_ms": event.duration_ms,
                "lines_changed": event.end_line - event.start_line + 1,
            },
        )

    def classify_batch(self, events: list[EditEvent]) -> list[Attribution]:
        """Classify a batch of events, grouping rapid sequences."""
        if not events:
            return []

        # Group events by file and time proximity
        groups = self._group_events(events)
        attributions = []

        for group in groups:
            if len(group) == 1:
                attributions.append(self.classify(group[0]))
            else:
                # Merge grouped events into a single attribution
                attributions.append(self._classify_group(group))

        return attributions

    def _group_events(self, events: list[EditEvent]) -> list[list[EditEvent]]:
        """Group events by file and temporal proximity."""
        groups: list[list[EditEvent]] = []
        current_group: list[EditEvent] = []

        for event in sorted(events, key=lambda e: (str(e.file), e.timestamp)):
            if not current_group:
                current_group = [event]
            elif (
                event.file == current_group[-1].file
                and event.timestamp - current_group[-1].timestamp <= self.config.grouping_window_ms
            ):
                current_group.append(event)
            else:
                groups.append(current_group)
                current_group = [event]

        if current_group:
            groups.append(current_group)

        return groups

    def _classify_group(self, events: list[EditEvent]) -> Attribution:
        """Classify a group of rapid events as a unit."""
        # Aggregate stats
        total_inserted = sum(len(e.inserted_text) for e in events)
        total_deleted = sum(len(e.deleted_text) for e in events)
        total_lines = sum(e.end_line - e.start_line + 1 for e in events)
        total_duration = sum(e.duration_ms for e in events)
        file = events[0].file
        start_line = min(e.start_line for e in events)
        end_line = max(e.end_line for e in events)

        # Heuristic scoring
        label, confidence = self._score_aggregate(
            total_inserted, total_deleted, total_lines, total_duration, events
        )

        return Attribution(
            file=file,
            start_line=start_line,
            end_line=end_line,
            label=label,
            confidence=confidence,
            source_hint=events[0].source_hint,
            metadata={
                "inserted_chars": total_inserted,
                "deleted_chars": total_deleted,
                "duration_ms": total_duration,
                "lines_changed": total_lines,
                "event_count": len(events),
                "grouped": True,
            },
        )

    def _score_event(self, event: EditEvent) -> tuple[AttributionLabel, float]:
        """Score a single event."""
        inserted_lines = event.inserted_text.count("\n") + (1 if event.inserted_text and not event.inserted_text.endswith("\n") else 0)
        deleted_lines = event.deleted_text.count("\n") + (1 if event.deleted_text and not event.deleted_text.endswith("\n") else 0)
        net_lines = inserted_lines - deleted_lines
        chars_per_ms = len(event.inserted_text) / max(event.duration_ms, 1)

        # Explicit source hint
        if event.source_hint in ("copilot", "cursor", "claude", "codeium", "tabnine"):
            return AttributionLabel.AI_GENERATED, 0.9

        # Bulk paste / multi-line accept
        if inserted_lines >= self.config.bulk_line_threshold:
            return AttributionLabel.AI_GENERATED, 0.85

        # Superhuman typing speed
        if chars_per_ms > self.config.speed_threshold_cpm:
            return AttributionLabel.AI_GENERATED, 0.75

        # Small, slow edits = human
        if net_lines <= 3 and chars_per_ms < 5.0 and event.duration_ms > 100:
            return AttributionLabel.HUMAN, 0.8

        # Modification of existing code (delete + insert) often human
        if deleted_lines > 0 and inserted_lines > 0 and net_lines == 0:
            return AttributionLabel.AI_MODIFIED, 0.65

        # Default to ambiguous
        return AttributionLabel.AMBIGUOUS, 0.5

    def _score_aggregate(
        self,
        inserted_chars: int,
        deleted_chars: int,
        lines: int,
        duration_ms: int,
        events: list[EditEvent],
    ) -> tuple[AttributionLabel, float]:
        """Score an aggregated group."""
        chars_per_ms = inserted_chars / max(duration_ms, 1)
        has_ai_hint = any(e.source_hint in ("copilot", "cursor", "claude", "codeium", "tabnine") for e in events)

        if has_ai_hint:
            return AttributionLabel.AI_GENERATED, 0.9

        if lines >= self.config.bulk_line_threshold:
            return AttributionLabel.AI_GENERATED, 0.85

        if chars_per_ms > self.config.speed_threshold_cpm:
            return AttributionLabel.AI_GENERATED, 0.75

        if lines <= 3 and chars_per_ms < 5.0 and duration_ms > 200:
            return AttributionLabel.HUMAN, 0.8

        if deleted_chars > 0 and inserted_chars > 0 and lines <= 5:
            return AttributionLabel.AI_MODIFIED, 0.65

        return AttributionLabel.AMBIGUOUS, 0.5

    def to_provenance_regions(self, attributions: list[Attribution]) -> list[ProvenanceRegion]:
        """Convert attributions to provenance regions for header writing."""
        regions = []
        for attr in attributions:
            regions.append(ProvenanceRegion(
                start_line=attr.start_line,
                end_line=attr.end_line,
                label=attr.label,
                confidence=attr.confidence,
                author=attr.source_hint or ("ai" if attr.label != AttributionLabel.HUMAN else "human"),
                rules=[],
            ))
        return self._merge_adjacent(regions)

    def _merge_adjacent(self, regions: list[ProvenanceRegion]) -> list[ProvenanceRegion]:
        """Merge adjacent regions with same label and similar confidence."""
        if not regions:
            return []

        merged = [regions[0]]
        for region in regions[1:]:
            last = merged[-1]
            if (
                region.start_line == last.end_line + 1
                and region.label == last.label
                and abs(region.confidence - last.confidence) < 0.2
            ):
                last.end_line = region.end_line
                last.confidence = (last.confidence + region.confidence) / 2
            else:
                merged.append(region)
        return merged
