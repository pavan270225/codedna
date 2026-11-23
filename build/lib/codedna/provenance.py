"""In-source provenance header format (round-trip safe)."""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .models import AttributionLabel, ProvenanceHeader as ModelProvenanceHeader, ProvenanceRegion


# Re-export the model classes
__all__ = ["extract_header", "inject_header", "remove_header", "get_comment_style"]


def get_comment_style(path: Path) -> tuple[str, str]:
    """Return (prefix, suffix) for the file's comment style."""
    patterns = {
        ".py": ("# codedna:", ""),
        ".js": ("// codedna:", ""),
        ".ts": ("// codedna:", ""),
        ".jsx": ("// codedna:", ""),
        ".tsx": ("// codedna:", ""),
        ".md": ("<!-- codedna:", "-->"),
        ".json": ("// codedna:", ""),  # JSONC
        ".yaml": ("# codedna:", ""),
        ".yml": ("# codedna:", ""),
    }
    return patterns.get(path.suffix.lower(), ("# codedna:", ""))


HEADER_REGEX = re.compile(
    r"(?:^|\n)(?:#|//|<!--)\s*codedna:(\{.*?\})(?:-->|$)",
    re.MULTILINE | re.DOTALL,
)


def extract_header(content: str) -> Optional[ModelProvenanceHeader]:
    """Extract provenance header from file content."""
    match = HEADER_REGEX.search(content)
    if not match:
        return None
    try:
        return ModelProvenanceHeader.from_json(match.group(1))
    except (json.JSONDecodeError, KeyError):
        return None


def inject_header(content: str, header: ModelProvenanceHeader, path: Path) -> str:
    """Inject or update provenance header in file content."""
    prefix, suffix = get_comment_style(path)
    header_line = f"{prefix}{header.to_json()}{suffix}"

    # Remove existing header
    content = HEADER_REGEX.sub("", content)

    # Insert at top (after shebang if present)
    lines = content.splitlines(keepends=True)
    insert_idx = 0
    if lines and lines[0].startswith("#!"):
        insert_idx = 1
    # Skip encoding declarations
    while insert_idx < len(lines) and lines[insert_idx].strip().startswith(("# -*-", "# coding:")):
        insert_idx += 1

    lines.insert(insert_idx, header_line + "\n")
    return "".join(lines)


def remove_header(content: str) -> str:
    """Remove provenance header from file content."""
    return HEADER_REGEX.sub("", content)