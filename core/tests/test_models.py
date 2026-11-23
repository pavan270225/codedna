"""Tests for core data models."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path

import pytest

from codedna.models import (
    Attribution,
    AttributionLabel,
    ProvenanceHeader,
    ProvenanceRegion,
)


class TestAttributionLabel:
    def test_colors(self):
        assert AttributionLabel.HUMAN.color == "#22c55e"
        assert AttributionLabel.AI_GENERATED.color == "#3b82f6"
        assert AttributionLabel.AI_MODIFIED.color == "#f97316"
        assert AttributionLabel.AMBIGUOUS.color == "#a855f7"

    def test_short_labels(self):
        assert AttributionLabel.HUMAN.short == "H"
        assert AttributionLabel.AI_GENERATED.short == "AI"
        assert AttributionLabel.AI_MODIFIED.short == "AIM"
        assert AttributionLabel.AMBIGUOUS.short == "?"


class TestAttribution:
    def test_creation(self):
        attr = Attribution(
            file=Path("test.py"),
            start_line=10,
            end_line=20,
            label=AttributionLabel.HUMAN,
            confidence=0.9,
        )
        assert attr.file == Path("test.py")
        assert attr.start_line == 10
        assert attr.end_line == 20
        assert attr.label == AttributionLabel.HUMAN
        assert attr.confidence == 0.9

    def test_length(self):
        attr = Attribution(
            file=Path("test.py"),
            start_line=10,
            end_line=20,
            label=AttributionLabel.HUMAN,
            confidence=0.9,
        )
        assert len(attr) == 11

    def test_to_from_dict(self):
        attr = Attribution(
            file=Path("test.py"),
            start_line=10,
            end_line=20,
            label=AttributionLabel.HUMAN,
            confidence=0.9,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            source_hint="copilot",
            metadata={"key": "value"},
        )
        d = attr.to_dict()
        assert d["file"] == "test.py"
        assert d["label"] == "human"
        assert d["confidence"] == 0.9

        attr2 = Attribution.from_dict(d)
        assert attr2.file == attr.file
        assert attr2.label == attr.label
        assert attr2.confidence == attr.confidence


class TestProvenanceRegion:
    def test_to_from_dict(self):
        region = ProvenanceRegion(
            start_line=10,
            end_line=20,
            label=AttributionLabel.AI_GENERATED,
            confidence=0.85,
            author="copilot",
            rules=["no-secrets"],
        )
        d = region.to_dict()
        assert d["start_line"] == 10
        assert d["label"] == "ai-generated"
        assert d["author"] == "copilot"

        region2 = ProvenanceRegion.from_dict(d)
        assert region2.start_line == region.start_line
        assert region2.label == region.label
        assert region2.author == region.author


class TestProvenanceHeader:
    def test_to_from_json(self):
        header = ProvenanceHeader(
            version=1,
            regions=[
                ProvenanceRegion(
                    start_line=10,
                    end_line=20,
                    label=AttributionLabel.HUMAN,
                    confidence=0.9,
                ),
                ProvenanceRegion(
                    start_line=21,
                    end_line=30,
                    label=AttributionLabel.AI_GENERATED,
                    confidence=0.85,
                    author="copilot",
                ),
            ],
            used_by=["vscode-extension", "cli"],
            rules=["type-hints", "no-secrets"],
        )
        json_str = header.to_json()
        header2 = ProvenanceHeader.from_json(json_str)

        assert header2.version == header.version
        assert len(header2.regions) == 2
        assert header2.regions[0].label == AttributionLabel.HUMAN
        assert header2.regions[1].label == AttributionLabel.AI_GENERATED
        assert header2.used_by == ["vscode-extension", "cli"]
        assert header2.rules == ["type-hints", "no-secrets"]

    def test_to_comment(self):
        header = ProvenanceHeader(
            regions=[
                ProvenanceRegion(
                    start_line=10,
                    end_line=20,
                    label=AttributionLabel.HUMAN,
                    confidence=0.9,
                )
            ]
        )
        py_comment = header.to_comment("python")
        assert py_comment.startswith("# codedna:")
        assert py_comment.endswith("\n")

        js_comment = header.to_comment("javascript")
        assert js_comment.startswith("// codedna:")

        md_comment = header.to_comment("markdown")
        assert md_comment.startswith("<!-- codedna:")
        assert md_comment.endswith("-->\n")

    def test_detect_language(self):
        assert ProvenanceHeader.detect_language(Path("test.py")) == "py"
        assert ProvenanceHeader.detect_language(Path("test.ts")) == "ts"
        assert ProvenanceHeader.detect_language(Path("test")) == "text"