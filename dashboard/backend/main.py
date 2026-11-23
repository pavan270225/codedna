"""FastAPI backend for CodeDNA web dashboard."""
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from codedna.store import Store
from codedna.models import AttributionLabel


# Global store instance
store = Store()


class RatioResponse(BaseModel):
    human: int
    ai: int
    total: int
    human_pct: float


class AttributionResponse(BaseModel):
    file: str
    start_line: int
    end_line: int
    label: str
    confidence: float
    timestamp: str
    source_hint: str | None = None


class FileRatioResponse(BaseModel):
    file: str
    human: int
    ai: int
    ambiguous: int
    human_pct: float


class DashboardSummary(BaseModel):
    total_files: int
    total_attributions: int
    human_lines: int
    ai_lines: int
    ambiguous_lines: int
    by_label: dict[str, int]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="CodeDNA Dashboard API",
    description="Web dashboard for CodeDNA AI-code attribution",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/summary", response_model=DashboardSummary)
async def get_summary() -> DashboardSummary:
    """Get overall dashboard summary."""
    all_attrs = store.get_all()
    human, ai = store.get_ratio()

    by_label: dict[str, int] = {}
    ambiguous = 0
    for attr in all_attrs:
        label = attr.label.value
        by_label[label] = by_label.get(label, 0) + len(attr)
        if attr.label == AttributionLabel.AMBIGUOUS:
            ambiguous += len(attr)

    return DashboardSummary(
        total_files=len(set(str(a.file) for a in all_attrs)),
        total_attributions=len(all_attrs),
        human_lines=human,
        ai_lines=ai,
        ambiguous_lines=ambiguous,
        by_label=by_label,
    )


@app.get("/api/ratio", response_model=RatioResponse)
async def get_global_ratio() -> RatioResponse:
    """Get global H/AI ratio."""
    human, ai = store.get_ratio()
    total = human + ai
    pct = (human / total * 100) if total > 0 else 0
    return RatioResponse(human=human, ai=ai, total=total, human_pct=pct)


@app.get("/api/ratio/{file_path:path}", response_model=FileRatioResponse)
async def get_file_ratio(file_path: str) -> FileRatioResponse:
    """Get H/AI ratio for a specific file."""
    from pathlib import Path
    attrs = store.get_for_file(Path(file_path))
    human = sum(len(a) for a in attrs if a.label == AttributionLabel.HUMAN)
    ai = sum(len(a) for a in attrs if a.label in {AttributionLabel.AI_GENERATED, AttributionLabel.AI_MODIFIED})
    ambiguous = sum(len(a) for a in attrs if a.label == AttributionLabel.AMBIGUOUS)
    total = human + ai + ambiguous
    pct = (human / total * 100) if total > 0 else 0
    return FileRatioResponse(
        file=file_path,
        human=human,
        ai=ai,
        ambiguous=ambiguous,
        human_pct=pct,
    )


@app.get("/api/attributions", response_model=list[AttributionResponse])
async def get_attributions(
    file: str | None = Query(None, description="Filter by file path"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[AttributionResponse]:
    """Get attribution records."""
    if file:
        attrs = store.get_for_file(Path(file))
    else:
        attrs = store.get_all()

    attrs = attrs[offset:offset + limit]

    return [
        AttributionResponse(
            file=str(a.file),
            start_line=a.start_line,
            end_line=a.end_line,
            label=a.label.value,
            confidence=a.confidence,
            timestamp=a.timestamp.isoformat(),
            source_hint=a.source_hint,
        )
        for a in attrs
    ]


@app.get("/api/files")
async def get_files() -> list[str]:
    """Get list of files with attribution data."""
    all_attrs = store.get_all()
    files = sorted(set(str(a.file) for a in all_attrs))
    return files


@app.get("/api/trends")
async def get_trends(days: int = Query(30, ge=1, le=365)) -> dict[str, Any]:
    """Get H/AI trends over time (placeholder for future implementation)."""
    from datetime import datetime, timedelta

    all_attrs = store.get_all()
    human, ai = store.get_ratio()

    return {
        "period_days": days,
        "current": {"human": human, "ai": ai},
        "daily": [],
        "message": "Trends require time-series data collection - not yet implemented",
    }


# Serve frontend static files
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"


@app.get("/")
async def serve_index():
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Frontend not built. Run `npm run build` in dashboard/frontend."}


@app.get("/{path:path}")
async def serve_static(path: str):
    file_path = frontend_dist / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(404, "Not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)