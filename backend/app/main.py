from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from pydantic import BaseModel

from app.config import settings


def _sanitize_q(q: str) -> str:
    return re.sub(r'[*(,)]', '', q).strip()


class PatchFavoriteBody(BaseModel):
    is_favorite: bool

app = FastAPI(title="Bug Bounty Writeups API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # front local (Vite)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/writeups")
def list_writeups(
    source: str | None = Query(default=None),
    year: int | None = Query(default=None, ge=2025),
    month: int | None = Query(default=None, ge=1, le=12),
    limit: int = Query(default=100, ge=1, le=500),
    q: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    if not settings.supabase_url or not settings.supabase_service_key:
        raise HTTPException(status_code=500, detail="Missing SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY")

    filters = ["select=id,source,title,url,author,summary,published_at,created_at,is_favorite"]
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
    if q:
        sanitized = _sanitize_q(q)
        if sanitized:
            filters.append(
                f"or=(title.ilike.*{sanitized}*,summary.ilike.*{sanitized}*)"
            )
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


@app.patch("/api/writeups/{writeup_id}", status_code=204, response_model=None)
def patch_favorite(writeup_id: UUID, body: PatchFavoriteBody) -> None:
    if not settings.supabase_url or not settings.supabase_service_key:
        raise HTTPException(status_code=500, detail="Missing SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY")
    endpoint = f"{settings.supabase_url}/rest/v1/writeups?id=eq.{writeup_id}"
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    try:
        response = requests.patch(endpoint, headers=headers, json={"is_favorite": body.is_favorite}, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Supabase update failed: {exc}") from exc
