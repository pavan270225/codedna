"""Tests for the heuristic classifier."""
from __future__ import annotations
from pathlib import Path

import pytest

from codedna.classifier import Classifier, ClassifierConfig, EditEvent
from codedna.models import AttributionLabel


class TestClassifierConfig:
    def test_defaults(self):
        cfg = ClassifierConfig()
        assert cfg.bulk_line_threshold == 10
        assert cfg.speed_threshold_cpm == 50.0
        assert cfg.min_confidence == 0.6
        assert cfg.grouping_window_ms == 500


class TestClassifier:
    def setup_method(self):
        self.classifier = Classifier()

    def test_ai_generated_from_source_hint(self):
        event = EditEvent(
            file=Path("test.py"),
            start_line=1,
            end_line=10,
            inserted_text="def hello():\n    return 'world'\n",
            deleted_text="",
            timestamp=1000,
            duration_ms=100,
            source_hint="copilot",
        )
        attr = self.classifier.classify(event)
        assert attr.label == AttributionLabel.AI_GENERATED
        assert attr.confidence == 0.9

    def test_ai_generated_bulk_lines(self):
        event = EditEvent(
            file=Path("test.py"),
            start_line=1,
            end_line=15,
            inserted_text="\n".join([f"line {i}" for i in range(15)]),
            deleted_text="",
            timestamp=1000,
            duration_ms=50,
            source_hint=None,
        )
        attr = self.classifier.classify(event)
        assert attr.label == AttributionLabel.AI_GENERATED
        assert attr.confidence >= 0.85

    def test_ai_generated_superhuman_speed(self):
        event = EditEvent(
            file=Path("test.py"),
            start_line=1,
            end_line=5,
            inserted_text="x" * 500,
            deleted_text="",
            timestamp=1000,
            duration_ms=1,
            source_hint=None,
        )
        attr = self.classifier.classify(event)
        assert attr.label == AttributionLabel.AI_GENERATED
        assert attr.confidence >= 0.75

    def test_human_typing(self):
        event = EditEvent(
            file=Path("test.py"),
            start_line=10,
            end_line=10,
            inserted_text="x = 1\n",
            deleted_text="",
            timestamp=1000,
            duration_ms=500,
            source_hint=None,
        )
        attr = self.classifier.classify(event)
        assert attr.label == AttributionLabel.HUMAN
        assert attr.confidence >= 0.8

    def test_ai_modified(self):
        event = EditEvent(
            file=Path("test.py"),
            start_line=10,
            end_line=10,
            inserted_text="x = 2\n",
            deleted_text="x = 1\n",
            timestamp=1000,
            duration_ms=100,
            source_hint=None,
        )
        attr = self.classifier.classify(event)
        assert attr.label == AttributionLabel.AI_MODIFIED
        assert attr.confidence >= 0.65

    def test_ambiguous_default(self):
        # This event falls in the "ambiguous" zone: not fast enough for AI,
        # not slow enough for human, no clear pattern
        event = EditEvent(
            file=Path("test.py"),
            start_line=10,
            end_line=10,
            inserted_text="x = 1 + 2\n",  # ~10 chars
            deleted_text="",
            timestamp=1000,
            duration_ms=50,  # 0.2 chars/ms - moderate speed
            source_hint=None,
        )
        attr = self.classifier.classify(event)
        assert attr.label == AttributionLabel.AMBIGUOUS
        assert attr.confidence == 0.5

    def test_classify_batch_groups_events(self):
        events = [
            EditEvent(
                file=Path("test.py"),
                start_line=1,
                end_line=1,
                inserted_text="line 1\n",
                deleted_text="",
                timestamp=1000,
                duration_ms=50,
            ),
            EditEvent(
                file=Path("test.py"),
                start_line=2,
                end_line=2,
                inserted_text="line 2\n",
                deleted_text="",
                timestamp=1000 + 100,  # Within 500ms grouping window
                duration_ms=50,
            ),
            EditEvent(
                file=Path("other.py"),
                start_line=1,
                end_line=1,
                inserted_text="other\n",
                deleted_text="",
                timestamp=2000,  # Different file, different time
                duration_ms=50,
            ),
        ]
        attrs = self.classifier.classify_batch(events)
        assert len(attrs) == 2  # Two groups

        # Find the grouped one (event_count == 2) and the single one
        grouped = next(a for a in attrs if a.metadata.get("event_count") == 2)
        single = next(a for a in attrs if a.metadata.get("event_count", 1) == 1)

        assert grouped.metadata.get("grouped") is True
        assert grouped.metadata["event_count"] == 2
        assert "grouped" not in single.metadata or single.metadata.get("grouped") is False

    def test_to_provenance_regions(self):
        attrs = [
            self.classifier.classify(EditEvent(
                file=Path("test.py"),
                start_line=1,
                end_line=5,
                inserted_text="code\n",
                deleted_text="",
                timestamp=1000,
                duration_ms=100,
                source_hint="copilot",
            )),
            self.classifier.classify(EditEvent(
                file=Path("test.py"),
                start_line=6,
                end_line=10,
                inserted_text="more\n",
                deleted_text="",
                timestamp=2000,
                duration_ms=500,
                source_hint=None,
            )),
        ]
        regions = self.classifier.to_provenance_regions(attrs)
        assert len(regions) == 2
        assert regions[0].label == AttributionLabel.AI_GENERATED
        assert regions[0].author == "copilot"
        assert regions[1].label == AttributionLabel.HUMAN
        assert regions[1].author == "human"

    def test_merge_adjacent_regions(self):
        attrs = [
            self.classifier.classify(EditEvent(
                file=Path("test.py"),
                start_line=1,
                end_line=5,
                inserted_text="code\n",
                deleted_text="",
                timestamp=1000,
                duration_ms=100,
                source_hint="copilot",
            )),
            self.classifier.classify(EditEvent(
                file=Path("test.py"),
                start_line=6,
                end_line=10,
                inserted_text="more\n",
                deleted_text="",
                timestamp=1000 + 100,
                duration_ms=50,
                source_hint="copilot",
            )),
        ]
        regions = self.classifier.to_provenance_regions(attrs)
        assert len(regions) == 1
        assert regions[0].start_line == 1
        assert regions[0].end_line == 10