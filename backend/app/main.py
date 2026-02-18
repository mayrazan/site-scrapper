from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query
import requests

from app.config import settings

app = FastAPI(title="Bug Bounty Writeups API", version="0.1.0")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/writeups")
def list_writeups(
    source: str | None = Query(default=None),
    year: int | None = Query(default=None, ge=2025),
    month: int | None = Query(default=None, ge=1, le=12),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    if not settings.supabase_url or not settings.supabase_service_key:
        raise HTTPException(status_code=500, detail="Missing SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY")

    filters = ["select=id,source,title,url,author,summary,published_at,created_at"]
    if source:
        filters.append(f"source=eq.{source}")
    if year:
        start = datetime(year, month or 1, 1).isoformat()
        if month == 12:
            end = datetime(year + 1, 1, 1).isoformat()
        elif month:
            end = datetime(year, month + 1, 1).isoformat()
        else:
            end = datetime(year + 1, 1, 1).isoformat()
        filters.append(f"published_at=gte.{start}")
        filters.append(f"published_at=lt.{end}")
    filters.append("order=published_at.desc")
    filters.append(f"limit={limit}")

    endpoint = f"{settings.supabase_url}/rest/v1/writeups?{'&'.join(filters)}"
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }
    try:
        response = requests.get(endpoint, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Supabase query failed: {exc}") from exc
    return response.json()
