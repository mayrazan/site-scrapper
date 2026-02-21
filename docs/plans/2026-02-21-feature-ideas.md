# Feature Ideas & Improvements

> Snapshot: 2026-02-21
> Based on current state: Python/FastAPI backend, React/Mantine frontend, Supabase Postgres, GitHub Actions daily scraper, sources: PortSwigger + Medium + HackerOne.

---

## Quick Wins (low effort, high value)

### 1. Favorites UI
The database already has a `preserve_favorites` flag and a cleanup function that respects it — but the frontend has no way to mark a writeup as a favorite. Adding a star button to `WriteupCard` and a filter toggle in `FilterBar` would complete this feature end-to-end without backend changes.

### 2. Full-text keyword search
The API (`/api/writeups`) has no search parameter. A `q=` query param filtered by `title.ilike.*{q}*` on Supabase, plus a search input in the `FilterBar`, would unlock a lot of value with minimal work.

### 3. CORS for production
`allow_origins` in `main.py` is hardcoded to `http://localhost:5173`. Before any real deployment this must be driven by an env variable (e.g. `CORS_ALLOWED_ORIGIN`) so the frontend domain can be configured without code changes.

### 4. Pagination
The API accepts up to 500 results but the frontend loads all of them in one request and shows them in a flat grid. Adding `offset` / `page` parameters and an "Load more" button (or infinite scroll via TanStack Query's `useInfiniteQuery`) avoids oversized payloads.

### 5. Read/unread tracking
Persist a `read_urls` set in `localStorage` on the frontend. Mark cards as "read" visually with a dimmed style, and let users hide read items with a toggle — zero backend cost.

---

## New Sources

### 6. Intigriti blog (RSS)
Intigriti publishes platform announcements and researcher spotlights at a predictable RSS endpoint. Same parser as PortSwigger — one new tuple in `collect_all_sources`.

### 7. YesWeHack blog (RSS)
Another major bug bounty platform with a public RSS feed. Same pattern.

### 8. Google Project Zero (RSS)
`https://googleprojectzero.blogspot.com/feeds/posts/default` — high-signal, low-noise source for serious vulnerability research.

### 9. Bugcrowd blog (RSS)
Another major platform. Adding it rounds out the big-4 coverage (HackerOne, Intigriti, YesWeHack, Bugcrowd).

### 10. GitHub search (REST API)
Search public repos for new `SECURITY.md`, CVE advisories, or PoC writeup READMEs using the GitHub Search API (`/search/repositories?q=bug+bounty+writeup`). Requires a GitHub token.

---

## Notifications Improvements

### 11. Email digest (SMTP / Resend)
Telegram and Discord cover real-time alerts well, but many people prefer email. A weekly HTML digest using Resend's free tier (3 000 emails/month) or plain SMTP would cover this without added infrastructure.

### 12. Keyword-based alerts
Instead of "all new writeups", let users configure keywords (e.g. `SSRF`, `OAuth`, `RCE`) and only send notifications when a matching writeup arrives. Store rules as a JSON env var or a small Supabase table.

### 13. Weekly digest mode
Add a second GitHub Actions schedule (Sunday 09:00 UTC) that sends a curated weekly roll-up of the top N writeups, rather than the current daily fire-hose.

---

## Frontend UX

### 14. Tags / vulnerability categories
Detect common vulnerability classes (XSS, SQLi, SSRF, IDOR, RCE, LFI, OAuth, JWT…) in the title or summary and auto-tag each writeup. Store tags in a Postgres array column and expose them as filter chips in the UI.

### 15. Stats / analytics page
A `/stats` route with simple Recharts or Chart.js charts:
- Writeups per source per month (bar chart)
- New writeups per day (sparkline)
- Top authors
- Distribution by vulnerability tag

This turns the aggregator into a lightweight threat-intel dashboard.

### 16. Export to CSV / JSON
A button in the FilterBar that downloads the currently filtered results as CSV or JSON. All data is already available client-side via TanStack Query — it's a one-function helper.

### 17. Dark mode toggle
Mantine ships a `useMantineColorScheme` hook and a `ColorSchemeScript` for SSR-safe theme switching. Adding a sun/moon icon button to the header connects the whole theme system in ~10 lines.

### 18. Shareable filter URLs
Sync filter state (`source`, `year`, `month`, `q`) to URL search params using React Router or `URLSearchParams + history.replaceState`. Users can bookmark or share a filtered view directly.

---

## Backend / Infrastructure

### 19. AI summarization (Claude API)
For writeups that have no summary (many HackerOne reports), call the Claude API (`claude-haiku-4-5`) with the title and truncated HTML to generate a 2–3 sentence summary at upsert time. Store in the existing `summary` column. Very cheap per token and removes the "Sem resumo disponível" fallback.

### 20. Expose own RSS feed
Add a `/api/rss` endpoint that returns the aggregated writeups as a valid RSS/Atom feed. This lets users subscribe in any RSS reader and closes the loop: the aggregator itself becomes a source.

### 21. Scrape failure alerts
When a source fails (already logged with `[warn]`), there's no alert. Send a Telegram/Discord message when any source returns 0 items or raises an exception, so silent failures don't go unnoticed for days.

### 22. Health dashboard endpoint
Extend `/api/health` to return per-source last-successful-scrape timestamps and writeup counts. The frontend could surface this as a small status indicator per source badge.

### 23. Rate-limit the API
The API has no authentication or rate limiting. Before making the backend publicly accessible, add a simple `slowapi` rate limiter (e.g. 60 req/min by IP) to avoid abuse of the Supabase proxy.

---

## Priority matrix

| Feature | Effort | Value | Suggested order |
|---|---|---|---|
| CORS env var (#3) | XS | Critical (deploy blocker) | 1 |
| Keyword search (#2) | S | High | 2 |
| Favorites UI (#1) | S | High | 3 |
| Pagination (#4) | S | Medium | 4 |
| Read/unread (#5) | XS | Medium | 5 |
| More RSS sources (#6–9) | XS each | Medium | 6 |
| Dark mode (#17) | XS | Low | 7 |
| Shareable URLs (#18) | S | Medium | 8 |
| Stats page (#15) | M | Medium | 9 |
| Keyword alerts (#12) | M | High | 10 |
| AI summarization (#19) | M | High | 11 |
| Email digest (#11) | M | Medium | 12 |
| Tags (#14) | M | Medium | 13 |
| Own RSS feed (#20) | S | Medium | 14 |
| Export CSV (#16) | XS | Low | 15 |
| Scrape failure alerts (#21) | XS | High | 16 |
| Weekly digest (#13) | XS | Medium | 17 |
| GitHub source (#10) | M | Medium | 18 |
| Health dashboard (#22) | S | Low | 19 |
| Rate limiting (#23) | S | Medium | 20 |

> Effort scale: XS < 1h · S 1–4h · M half-day · L full day+
