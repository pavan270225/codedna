"""Stdio-based IPC server for VS Code extension communication."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Attribution, AttributionLabel, ProvenanceHeader, ProvenanceRegion
from .store import Store
from .classifier import Classifier, ClassifierConfig, EditEvent
from .header import HeaderWriter
from .llm_classifier import LLMClassifier


@dataclass
class Request:
    """Incoming request from extension."""
    id: int
    method: str
    params: dict[str, Any]


@dataclass
class Response:
    """Outgoing response to extension."""
    id: int
    result: Any | None = None
    error: str | None = None

    def to_json(self) -> str:
        if self.error:
            return json.dumps({"jsonrpc": "2.0", "id": self.id, "error": {"message": self.error}})
        return json.dumps({"jsonrpc": "2.0", "id": self.id, "result": self.result})


class IPCServer:
    """JSON-RPC 2.0 over stdio."""

    def __init__(self, llm_classifier: LLMClassifier | None = None):
        self.store = Store()
        self.classifier = Classifier()
        self.llm_classifier = llm_classifier
        self.writer = HeaderWriter(enabled=True)
        self._request_id = 0

    async def run(self) -> None:
        """Main event loop reading from stdin, writing to stdout."""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, asyncio.get_event_loop())

        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                line = line.decode().strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                    response = await self.handle_request(request)
                    writer.write((response.to_json() + "\n").encode())
                    await writer.drain()
                except json.JSONDecodeError:
                    err = Response(id=-1, error="Invalid JSON")
                    writer.write((err.to_json() + "\n").encode())
                    await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def handle_request(self, request: dict[str, Any]) -> Response:
        req_id = request.get("id", -1)
        method = request.get("method", "")
        params = request.get("params", {})

        try:
            if method == "classify":
                result = await self.handle_classify(params)
            elif method == "get_ratio":
                result = await self.handle_get_ratio(params)
            elif method == "write_header":
                result = await self.handle_write_header(params)
            elif method == "remove_header":
                result = await self.handle_remove_header(params)
            elif method == "read_header":
                result = await self.handle_read_header(params)
            elif method == "get_status":
                result = await self.handle_get_status(params)
            elif method == "ping":
                result = {"status": "ok"}
            else:
                return Response(id=req_id, error=f"Unknown method: {method}")

            return Response(id=req_id, result=result)

        except Exception as e:
            return Response(id=req_id, error=str(e))

    async def handle_classify(self, params: dict[str, Any]) -> dict[str, Any]:
        """Classify edit events."""
        events_data = params.get("events", [])
        events = []

        for e in events_data:
            events.append(EditEvent(
                file=Path(e["file"]),
                start_line=e["start_line"],
                end_line=e["end_line"],
                inserted_text=e.get("inserted_text", ""),
                deleted_text=e.get("deleted_text", ""),
                timestamp=e["timestamp"],
                duration_ms=e["duration_ms"],
                source_hint=e.get("source_hint"),
            ))

        # Use LLM classifier if available, otherwise fallback to heuristic
        if self.llm_classifier and self.llm_classifier.enabled:
            attributions = await self.llm_classifier.classify_batch(events)
        else:
            attributions = self.classifier.classify_batch(events)

        for attr in attributions:
            self.store.add(attr)

        return {"attributions": [a.to_dict() for a in attributions]}

    async def handle_get_ratio(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get H/AI ratio for a file or globally."""
        file = params.get("file")
        if file:
            human, ai = self.store.get_ratio(Path(file))
        else:
            human, ai = self.store.get_ratio()

        total = human + ai
        pct = (human / total * 100) if total > 0 else 0
        return {"human": human, "ai": ai, "total": total, "human_pct": pct}

    async def handle_get_attributions(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get all attributions for a file."""
        file = params.get("file")
        if not file:
            return {"attributions": []}

        attrs = self.store.get_for_file(Path(file))
        return {"attributions": [a.to_dict() for a in attrs]}

    async def handle_write_header(self, params: dict[str, Any]) -> dict[str, Any]:
        """Write provenance header to a file."""
        file = Path(params["file"])
        attrs = self.store.get_for_file(file)

        if not attrs:
            return {"success": False, "error": "No attribution data for file"}

        regions = self.classifier.to_provenance_regions(attrs)
        header = ProvenanceHeader(regions=regions)

        success = self.writer.write_header(file, header)
        return {"success": success}

    async def handle_remove_header(self, params: dict[str, Any]) -> dict[str, Any]:
        """Remove provenance header from a file."""
        file = Path(params["file"])
        success = self.writer.remove_header(file)
        return {"success": success}

    async def handle_read_header(self, params: dict[str, Any]) -> dict[str, Any]:
        """Read provenance header from a file."""
        file = Path(params["file"])
        header = HeaderParser.parse_file(file)
        if header:
            return {"header": {
                "version": header.version,
                "regions": [r.to_dict() for r in header.regions],
                "used_by": header.used_by,
                "rules": header.rules,
                "updated_at": header.updated_at.isoformat(),
            }}
        return {"header": None}

    async def handle_get_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get overall status."""
        all_attrs = self.store.get_all()
        human, ai = self.store.get_ratio()

        by_label: dict[str, int] = {}
        for attr in all_attrs:
            by_label[attr.label.value] = by_label.get(attr.label.value, 0) + len(attr)

        return {
            "total_files": len(set(str(a.file) for a in all_attrs)),
            "total_attributions": len(all_attrs),
            "human_lines": human,
            "ai_lines": ai,
            "by_label": by_label,
        }


# Import here to avoid circular
from .header import HeaderParser
