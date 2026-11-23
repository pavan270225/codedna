"""In-source provenance header writer and parser."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import ProvenanceHeader, ProvenanceRegion, AttributionLabel


class HeaderWriter:
    """Write and manage codedna: provenance headers in source files."""

    HEADER_PATTERN = re.compile(
        r'^(?:(?://|#|<!--|%)\s*)?codedna:\s*(\{.*?\})\s*(?:-->)?\s*$',
        re.MULTILINE
    )

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def write_header(self, file_path: Path, header: ProvenanceHeader) -> bool:
        """Write or update the provenance header in a file."""
        if not self.enabled:
            return False

        content = file_path.read_text(encoding="utf-8")
        language = ProvenanceHeader.detect_language(file_path)
        comment = header.to_comment(language)

        # Check if header already exists
        match = self.HEADER_PATTERN.search(content)
        if match:
            # Replace existing header
            new_content = self.HEADER_PATTERN.sub(comment.rstrip(), content, count=1)
        else:
            # Insert at top of file (after shebang if present)
            new_content = self._insert_at_top(content, comment)

        if new_content != content:
            file_path.write_text(new_content, encoding="utf-8")
            return True
        return False

    def _insert_at_top(self, content: str, comment: str) -> str:
        """Insert header at top, preserving shebang."""
        lines = content.splitlines(keepends=True)
        if lines and lines[0].startswith("#!"):
            return lines[0] + comment + "".join(lines[1:])
        return comment + content

    def remove_header(self, file_path: Path) -> bool:
        """Remove the codedna header from a file."""
        content = file_path.read_text(encoding="utf-8")
        match = self.HEADER_PATTERN.search(content)
        if match:
            new_content = self.HEADER_PATTERN.sub("", content, count=1)
            file_path.write_text(new_content, encoding="utf-8")
            return True
        return False

    def read_header(self, file_path: Path) -> ProvenanceHeader | None:
        """Read and parse the codedna header from a file."""
        content = file_path.read_text(encoding="utf-8")
        match = self.HEADER_PATTERN.search(content)
        if match:
            try:
                return ProvenanceHeader.from_json(match.group(1))
            except Exception:
                return None
        return None

    def has_header(self, file_path: Path) -> bool:
        """Check if file has a codedna header."""
        content = file_path.read_text(encoding="utf-8")
        return bool(self.HEADER_PATTERN.search(content))


class HeaderParser:
    """Parse codedna headers from various comment styles."""

    # Patterns for different comment styles
    PATTERNS = [
        # Python, shell, etc.
        re.compile(r'^#\s*codedna:\s*(\{.*?\})\s*$', re.MULTILINE),
        # JavaScript, TypeScript, Java, Go, Rust, C++, etc.
        re.compile(r'^//\s*codedna:\s*(\{.*?\})\s*$', re.MULTILINE),
        # HTML, XML, Markdown
        re.compile(r'^<!--\s*codedna:\s*(\{.*?\})\s*-->\s*$', re.MULTILINE),
        # LaTeX
        re.compile(r'^%\s*codedna:\s*(\{.*?\})\s*$', re.MULTILINE),
    ]

    @classmethod
    def parse(cls, content: str) -> ProvenanceHeader | None:
        """Extract and parse codedna header from file content."""
        for pattern in cls.PATTERNS:
            match = pattern.search(content)
            if match:
                try:
                    return ProvenanceHeader.from_json(match.group(1))
                except Exception:
                    continue
        return None

    @classmethod
    def parse_file(cls, file_path: Path) -> ProvenanceHeader | None:
        """Parse codedna header from a file."""
        content = file_path.read_text(encoding="utf-8")
        return cls.parse(content)


def round_trip_test(file_path: Path, header: ProvenanceHeader) -> bool:
    """Test that writing and reading a header preserves data."""
    writer = HeaderWriter(enabled=True)
    original_content = file_path.read_text(encoding="utf-8")

    try:
        # Write header
        writer.write_header(file_path, header)

        # Read it back
        read_header = HeaderParser.parse_file(file_path)

        # Restore original
        file_path.write_text(original_content, encoding="utf-8")

        if read_header is None:
            return False

        # Compare key fields
        return (
            read_header.version == header.version
            and len(read_header.regions) == len(header.regions)
            and read_header.used_by == header.used_by
            and read_header.rules == header.rules
        )
    except Exception:
        # Restore on error
        file_path.write_text(original_content, encoding="utf-8")
        return False
