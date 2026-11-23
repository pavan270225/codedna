"""Core data models for CodeDNA."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
import json


class AttributionLabel(str, Enum):
    """Classification of an edit's origin."""

    HUMAN = "human"
    AI_GENERATED = "ai-generated"
    AI_MODIFIED = "ai-modified"
    AMBIGUOUS = "ambiguous"

    @property
    def color(self) -> str:
        """VS Code gutter decoration color."""
        return {
            AttributionLabel.HUMAN: "#22c55e",      # green-500
            AttributionLabel.AI_GENERATED: "#3b82f6",  # blue-500
            AttributionLabel.AI_MODIFIED: "#f97316",   # orange-500
            AttributionLabel.AMBIGUOUS: "#a855f7",     # purple-500
        }[self]

    @property
    def short(self) -> str:
        """Short label for status bar."""
        return {
            AttributionLabel.HUMAN: "H",
            AttributionLabel.AI_GENERATED: "AI",
            AttributionLabel.AI_MODIFIED: "AIM",
            AttributionLabel.AMBIGUOUS: "?",
        }[self]


@dataclass(slots=True)
class Attribution:
    """A single attributed edit region."""

    file: Path
    start_line: int
    end_line: int
    label: AttributionLabel
    confidence: float  # 0.0 - 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    source_hint: str | None = None  # e.g., "copilot", "cursor", "bulk-paste"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": str(self.file),
            "start_line": self.start_line,
            "end_line": self.end_line,
            "label": self.label.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "source_hint": self.source_hint,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Attribution:
        return cls(
            file=Path(data["file"]),
            start_line=data["start_line"],
            end_line=data["end_line"],
            label=AttributionLabel(data["label"]),
            confidence=data["confidence"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source_hint=data.get("source_hint"),
            metadata=data.get("metadata", {}),
        )

    def __len__(self) -> int:
        return self.end_line - self.start_line + 1


@dataclass(slots=True)
class ProvenanceRegion:
    """A region in a file with provenance metadata."""

    start_line: int
    end_line: int
    label: AttributionLabel
    confidence: float
    author: str | None = None  # e.g., "human", "copilot", "claude"
    rules: list[str] = field(default_factory=list)  # e.g., ["no-secrets", "type-hints"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_line": self.start_line,
            "end_line": self.end_line,
            "label": self.label.value,
            "confidence": self.confidence,
            "author": self.author,
            "rules": self.rules,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProvenanceRegion:
        return cls(
            start_line=data["start_line"],
            end_line=data["end_line"],
            label=AttributionLabel(data["label"]),
            confidence=data["confidence"],
            author=data.get("author"),
            rules=data.get("rules", []),
        )


@dataclass(slots=True)
class ProvenanceHeader:
    """In-source provenance header (codedna: block)."""

    version: int = 1
    regions: list[ProvenanceRegion] = field(default_factory=list)
    used_by: list[str] = field(default_factory=list)  # agent IDs that read this
    rules: list[str] = field(default_factory=list)    # repo-wide rules
    updated_at: datetime = field(default_factory=datetime.now)

    def to_json(self) -> str:
        return json.dumps({
            "version": self.version,
            "regions": [r.to_dict() for r in self.regions],
            "used_by": self.used_by,
            "rules": self.rules,
            "updated_at": self.updated_at.isoformat(),
        }, separators=(",", ":"))

    @classmethod
    def from_json(cls, json_str: str) -> ProvenanceHeader:
        data = json.loads(json_str)
        return cls(
            version=data.get("version", 1),
            regions=[ProvenanceRegion.from_dict(r) for r in data.get("regions", [])],
            used_by=data.get("used_by", []),
            rules=data.get("rules", []),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )

    def to_comment(self, language: str) -> str:
        """Render as a language-appropriate comment block."""
        json_str = self.to_json()
        comment_map = {
            "python": f"# codedna: {json_str}\n",
            "javascript": f"// codedna: {json_str}\n",
            "typescript": f"// codedna: {json_str}\n",
            "java": f"// codedna: {json_str}\n",
            "go": f"// codedna: {json_str}\n",
            "rust": f"// codedna: {json_str}\n",
            "cpp": f"// codedna: {json_str}\n",
            "c": f"// codedna: {json_str}\n",
            "csharp": f"// codedna: {json_str}\n",
            "ruby": f"# codedna: {json_str}\n",
            "php": f"// codedna: {json_str}\n",
            "swift": f"// codedna: {json_str}\n",
            "kotlin": f"// codedna: {json_str}\n",
            "scala": f"// codedna: {json_str}\n",
            "r": f"# codedna: {json_str}\n",
            "julia": f"# codedna: {json_str}\n",
            "shell": f"# codedna: {json_str}\n",
            "bash": f"# codedna: {json_str}\n",
            "zsh": f"# codedna: {json_str}\n",
            "fish": f"# codedna: {json_str}\n",
            "dockerfile": f"# codedna: {json_str}\n",
            "yaml": f"# codedna: {json_str}\n",
            "yml": f"# codedna: {json_str}\n",
            "toml": f"# codedna: {json_str}\n",
            "ini": f"# codedna: {json_str}\n",
            "cfg": f"# codedna: {json_str}\n",
            "conf": f"# codedna: {json_str}\n",
            "properties": f"# codedna: {json_str}\n",
            "json": f"// codedna: {json_str}\n",
            "html": f"<!-- codedna: {json_str} -->\n",
            "xml": f"<!-- codedna: {json_str} -->\n",
            "markdown": f"<!-- codedna: {json_str} -->\n",
            "md": f"<!-- codedna: {json_str} -->\n",
            "tex": f"% codedna: {json_str}\n",
            "latex": f"% codedna: {json_str}\n",
        }
        return comment_map.get(language.lower(), f"// codedna: {json_str}\n")

    @classmethod
    def detect_language(cls, path: Path) -> str:
        suffix = path.suffix.lower().lstrip(".")
        return suffix if suffix else "text"
