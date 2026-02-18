from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import json
import re
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
        author = (node.findtext("author") or node.findtext("dc:creator") or "").strip()
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


def parse_hackerone_overview_html(html: str) -> list[dict]:
    pattern = re.compile(r'<a[^>]+href=["\'](/reports/\d+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
    items: list[dict] = []
    now = datetime.now(timezone.utc)
    for href, label in pattern.findall(html):
        title = re.sub(r"\s+", " ", unescape(re.sub(r"<.*?>", "", label))).strip()
        if not title:
            title = f"HackerOne Report {href.split('/')[-1]}"
        items.append(
            WriteupItem(
                source="hackerone",
                title=title,
                url=f"https://hackerone.com{href}",
                published_at=now,
            ).to_record()
        )
    return items


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

    res = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    res.raise_for_status()
    return res.text


def collect_all_sources() -> list[dict]:
    all_items: list[dict] = []

    portswigger_xml = _get("https://portswigger.net/research/rss")
    all_items.extend(parse_rss_items(portswigger_xml, source="portswigger"))

    medium_xml = _get("https://medium.com/feed/tag/bug-bounty")
    all_items.extend(parse_rss_items(medium_xml, source="medium"))

    hackerone_html = _get("https://hackerone.com/hacktivity/overview")
    # Best-effort extraction from rendered page and JSON blobs.
    all_items.extend(parse_hackerone_overview_html(hackerone_html))
    if not any(item["source"] == "hackerone" for item in all_items):
        json_links = re.findall(r'"url":"(https:\\/\\/hackerone.com\\/reports\\/\d+)"', hackerone_html)
        now = datetime.now(timezone.utc)
        for raw_url in json_links:
            all_items.append(
                WriteupItem(
                    source="hackerone",
                    title=f"HackerOne Report {raw_url.split('/')[-1]}",
                    url=raw_url.replace("\\/", "/"),
                    published_at=now,
                ).to_record()
            )

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
