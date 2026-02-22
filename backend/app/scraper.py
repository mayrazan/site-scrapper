from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
from typing import Iterable
from urllib.parse import quote
import xml.etree.ElementTree as ET

MIN_DATE = datetime(2025, 1, 1, tzinfo=timezone.utc)
USER_AGENT = "site-scrapper/1.0 (+https://github.com/)"


@dataclass
class WriteupItem:
    source: str
    title: str
    url: str
    published_at: datetime
    author: str | None = None
    summary: str | None = None

    def to_record(self) -> dict:
        record = asdict(self)
        record["published_at"] = self.published_at.isoformat()
        return record


def _force_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_date(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        return _force_utc(parsedate_to_datetime(raw))
    except (TypeError, ValueError):
        pass
    try:
        return _force_utc(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    except ValueError:
        return datetime.now(timezone.utc)


def parse_rss_items(xml_text: str, source: str) -> list[dict]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    items: list[dict] = []
    for node in root.findall(".//item"):
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()
        pub_date = node.findtext("pubDate") or node.findtext("published")
        desc = (node.findtext("description") or "").strip()
        author = (
            node.findtext("author")
            or node.findtext("{http://purl.org/dc/elements/1.1/}creator")
            or ""
        ).strip()
        if not link or not title:
            continue
        items.append(
            WriteupItem(
                source=source,
                title=title,
                url=link,
                published_at=_parse_date(pub_date),
                author=author or None,
                summary=desc or None,
            ).to_record()
        )
    return items


def parse_hackerone_hacktivity_api(payload: dict) -> list[dict]:
    items: list[dict] = []
    seen_urls: set[str] = set()
    included_reports: dict[str, dict] = {}

    for entry in payload.get("included") or []:
        if entry.get("type") != "report":
            continue
        report_id = str(entry.get("id") or "").strip()
        if report_id:
            included_reports[report_id] = entry

    for entry in payload.get("data") or []:
        attrs = entry.get("attributes") or {}
        report_link = (
            entry.get("relationships", {})
            .get("report", {})
            .get("data", {})
        )
        report_id = str(report_link.get("id") or "").strip()
        report_entry = included_reports.get(report_id, {})
        report_attrs = report_entry.get("attributes") or {}

        url = (
            report_attrs.get("url")
            or attrs.get("url")
            or attrs.get("report_url")
            or ""
        ).strip()
        if not url and report_id.isdigit():
            url = f"https://hackerone.com/reports/{report_id}"
        if not url:
            continue
        if not url.startswith("http"):
            if url.startswith("/reports/"):
                url = f"https://hackerone.com{url}"
            else:
                continue
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title = (
            report_attrs.get("title")
            or attrs.get("title")
            or (f"HackerOne Report {report_id}" if report_id else "HackerOne report")
        )
        published_raw = (
            report_attrs.get("disclosed_at")
            or attrs.get("disclosed_at")
            or attrs.get("published_at")
            or attrs.get("created_at")
        )
        items.append(
            WriteupItem(
                source="hackerone",
                title=title.strip(),
                url=url,
                published_at=_parse_date(published_raw),
            ).to_record()
        )

    return items


def fetch_hackerone_hacktivity_api(username: str, api_token: str) -> list[dict]:
    import requests

    endpoint = "https://api.hackerone.com/v1/hackers/hacktivity?page[size]=100&queryString=disclosed:true"
    collected: list[dict] = []

    for _ in range(3):
        resp = requests.get(
            endpoint,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            auth=(username, api_token),
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        collected.extend(parse_hackerone_hacktivity_api(payload))
        next_url = (payload.get("links") or {}).get("next")
        if not next_url:
            break
        endpoint = next_url

    return dedupe_items(collected)


def filter_recent_items(items: Iterable[dict]) -> list[dict]:
    out: list[dict] = []
    for item in items:
        value = item.get("published_at")
        if isinstance(value, str):
            date_value = _parse_date(value)
        elif isinstance(value, datetime):
            date_value = _force_utc(value)
        else:
            date_value = datetime.now(timezone.utc)
        if date_value >= MIN_DATE:
            new_item = dict(item)
            new_item["published_at"] = date_value
            out.append(new_item)
    return out


def dedupe_items(items: Iterable[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in items:
        url = (item.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(item)
    return deduped


def _get(url: str) -> str:
    import requests
    import time

    max_attempts = 4
    backoff_seconds = 2.0
    for attempt in range(max_attempts):
        try:
            res = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
            if res.status_code == 429 and attempt < max_attempts - 1:
                retry_after = res.headers.get("Retry-After")
                wait_seconds = float(retry_after) if retry_after and retry_after.isdigit() else backoff_seconds * (2**attempt)
                time.sleep(min(wait_seconds, 30.0))
                continue
            res.raise_for_status()
            return res.text
        except requests.RequestException as exc:
            response = getattr(exc, "response", None)
            status = getattr(response, "status_code", None)
            retriable = status in {429, 500, 502, 503, 504} or status is None
            if not retriable or attempt >= max_attempts - 1:
                raise
            time.sleep(min(backoff_seconds * (2**attempt), 30.0))

    raise RuntimeError(f"failed to fetch {url}")


def collect_all_sources(
    hackerone_username: str | None = None,
    hackerone_api_token: str | None = None,
) -> list[dict]:
    all_items: list[dict] = []
    sources: list[tuple[str, str, callable]] = [
        ("portswigger", "https://portswigger.net/research/rss", lambda body: parse_rss_items(body, source="portswigger")),
        ("medium", "https://medium.com/feed/tag/bug-bounty", lambda body: parse_rss_items(body, source="medium")),
    ]

    for source_name, source_url, parser in sources:
        try:
            source_body = _get(source_url)
            all_items.extend(parser(source_body))
        except Exception as exc:
            print(f"[warn] failed collecting source={source_name} url={source_url}: {exc}")

    h1_user = (hackerone_username or os.getenv("HACKERONE_USERNAME") or "").strip()
    h1_token = (hackerone_api_token or os.getenv("HACKERONE_API_TOKEN") or "").strip()

    if h1_user and h1_token:
        try:
            all_items.extend(fetch_hackerone_hacktivity_api(h1_user, h1_token))
        except Exception as exc:
            print("[warn] failed collecting source=hackerone via api: " f"{exc}")
    else:
        print("[warn] skipping hackerone api: HACKERONE_USERNAME/HACKERONE_API_TOKEN not configured")

    return dedupe_items(filter_recent_items(all_items))


def _supabase_headers(service_role_key: str) -> dict:
    return {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
    }


def fetch_existing_urls(supabase_url: str, service_role_key: str, urls: list[str]) -> set[str]:
    import requests

    if not urls:
        return set()
    existing: set[str] = set()
    headers = _supabase_headers(service_role_key)
    for i in range(0, len(urls), 100):
        chunk = urls[i : i + 100]
        encoded = ",".join(quote(u, safe="") for u in chunk)
        endpoint = f"{supabase_url}/rest/v1/writeups?select=url&url=in.({encoded})"
        resp = requests.get(endpoint, headers=headers, timeout=30)
        resp.raise_for_status()
        for row in resp.json():
            if row.get("url"):
                existing.add(row["url"])
    return existing


def upsert_items_to_supabase(supabase_url: str, service_role_key: str, items: list[dict]) -> int:
    import requests

    if not items:
        return 0
    endpoint = f"{supabase_url}/rest/v1/writeups?on_conflict=url"
    headers = _supabase_headers(service_role_key)
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    payload = []
    for item in items:
        row = dict(item)
        if isinstance(row.get("published_at"), datetime):
            row["published_at"] = row["published_at"].isoformat()
        payload.append(row)
    resp = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=60)
    resp.raise_for_status()
    return len(payload)


def send_telegram_message(bot_token: str, chat_id: str, message: str) -> None:
    import requests

    if not bot_token or not chat_id:
        return
    endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(endpoint, json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True}, timeout=30).raise_for_status()


def send_discord_message(webhook_url: str, message: str) -> None:
    import requests

    if not webhook_url:
        return
    requests.post(webhook_url, json={"content": message}, timeout=30).raise_for_status()


def format_daily_digest(items: list[dict]) -> str:
    if not items:
        return "Nenhum novo write-up hoje."
    lines = ["Novos write-ups de bug bounty:"]
    for item in items[:15]:
        lines.append(f"- [{item['source']}] {item['title']}\n  {item['url']}")
    if len(items) > 15:
        lines.append(f"... e mais {len(items) - 15}")
    return "\n".join(lines)
