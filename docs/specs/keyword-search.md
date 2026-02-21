# Spec: Full-Text Keyword Search

> Status: Draft | Linear: N/A | Date: 2026-02-21

## Problem Statement

Users browsing the writeups aggregator have no way to find writeups by topic. With hundreds of
entries across PortSwigger, Medium, and HackerOne, discovering writeups about a specific
vulnerability class (e.g. "SSRF", "OAuth", "RCE") requires manually scanning the grid —
or not finding them at all. Adding a keyword search unlocks the core value of the aggregator
as a reference tool.

## Goals

- Users can type a keyword and receive only writeups whose title or summary contains that keyword.
- Search works alongside existing source / year / month filters (all active filters apply together).
- When no results match, the user sees a clear empty-state message with a way to reset.

## Non-Goals (Out of Scope)

- Full-text search over writeup body/content (only title and summary are stored).
- Author or URL search.
- Real-time / debounced search — query submits on Enter only.
- Search history or saved queries.
- Minimum query length enforcement or spell correction.

## User Stories

- As a user, I want to type a keyword in a search box and press Enter so that I only see writeups
  related to that topic.
- As a user, I want search to combine with my active source/year/month filters so that I can
  narrow results precisely (e.g. HackerOne writeups about IDOR from 2024).
- As a user, I want to clear my search and return to the unfiltered view easily.
- As a user, I want to know when no writeups match my query so that I don't think the page is broken.

## Functional Requirements

- `GET /api/writeups` must accept an optional `q` query parameter (string, no minimum length).
- When `q` is present and non-empty, the Supabase query must use PostgREST's `or=` filter to match
  rows where **title ilike `*q*`** OR **summary ilike `*q*`** (case-insensitive, substring match).
- When `q` is absent or empty, the endpoint behaves exactly as today.
- The `q` parameter must be sanitized server-side before being interpolated into the PostgREST
  filter string (strip `*`, `(`, `)`, `,` characters to prevent filter injection).
- `q` composes with all other filters (`source`, `year`, `month`, `limit`) — all active filters
  apply as AND conditions.
- `WriteupFilters` in `frontend/src/lib/api.ts` must gain a `q: string` field (empty string = no search).
- `fetchWriteups` must pass `q` as a URL param when non-empty.
- `FilterBar` must display a `TextInput` (Mantine) with label "Buscar" and placeholder
  "Título ou resumo…" above or before the existing Select dropdowns.
- The search input maintains its own local state; it only calls `onChange` (propagating to
  `WriteupFilters`) when the user presses Enter or clicks a search icon button.
- Pressing Enter with an empty input clears the active search (sets `q` back to `''`).
- The "Limpar filtros" button must also reset the search input (`q: ''`) in addition to
  source/year/month.
- When the returned writeup list is empty **and** a non-empty `q` is active, the UI shows an
  empty-state message (see Edge Cases).

## Acceptance Criteria

- [ ] A text input labeled "Buscar" appears in the `FilterBar`.
- [ ] Typing "SSRF" and pressing Enter fetches `/api/writeups?q=SSRF` (plus any active filters).
- [ ] The API response contains only writeups whose title or summary includes "ssrf"
  (case-insensitive).
- [ ] Combining search with source filter (e.g. `source=hackerone&q=IDOR`) returns only matching
  HackerOne writeups.
- [ ] When no writeups match, the grid area shows the empty-state message instead of a blank grid.
- [ ] Clicking "Limpar filtros" clears both the dropdown filters and the search input.
- [ ] Typing in the input but not pressing Enter does **not** trigger a new API request.
- [ ] A writeup with a matching summary but non-matching title is included in results.
- [ ] The `q` value is sanitized: characters `* ( ) ,` are stripped before the PostgREST filter
  is built.

## Edge Cases & Error States

- **No results**: When `q` is non-empty and the API returns an empty array, show:
  *"Nenhum writeup encontrado para "[query]". Tente outros termos ou limpe a busca."*
  Include a "Limpar busca" button that resets `q` to `''`.
- **Summary is null**: `ilike` on a null column returns null in PostgreSQL (treated as false) —
  the row is excluded correctly; no special handling needed.
- **Very long query string**: No maximum enforced by spec; browser URL length limits apply.
  The `q` value should be trimmed of leading/trailing whitespace before use.
- **Special characters**: Characters with PostgREST filter significance (`*`, `(`, `)`, `,`) are
  stripped server-side. The user may still submit queries with spaces, hyphens, or punctuation —
  these are passed through as-is since PostgREST handles them correctly in `ilike`.
- **Enter pressed with whitespace-only input**: Treat as empty; reset `q` to `''` without
  making an API call.

## Technical Constraints

- **`backend/app/main.py`** — Add `q: str | None = Query(default=None)` to `list_writeups`.
  When present, append `or=(title.ilike.*{sanitized_q}*,summary.ilike.*{sanitized_q}*)` to the
  `filters` list. Sanitize by stripping `*`, `(`, `)`, `,` from `q` before interpolation.
- **`frontend/src/lib/api.ts`** — Add `q: string` to `WriteupFilters`. Add `q` to `initialFilters`
  (empty string). In `fetchWriteups`, add `if (filters.q) params.set('q', filters.q)`.
- **`frontend/src/components/FilterBar.tsx`** — Add `TextInput` from `@mantine/core` (already
  installed). Add local `useState<string>` for the input value. Wire `onKeyDown` to detect Enter
  and call `onChange({ ...filters, q: trimmedValue })`. The "Limpar filtros" button's `onClick`
  must also reset the local input state.
- No new backend dependencies required. No database schema changes.
- No authentication or authorization changes.

## Open Questions

None — all questions resolved before writing.

## Minor Assumptions

- UI copy is in Portuguese to match existing labels.
- No minimum query length is enforced (single characters are valid).
- Whitespace-only input is treated as empty/no-search.
- The search `TextInput` is placed before the source/year/month `Select` dropdowns in `FilterBar`
  (leftmost position in the filter grid) as it is the primary filter action.

## References

- Linear: N/A
- Feature ideas file: `docs/plans/2026-02-21-feature-ideas.md` — item #2
- Related files: `backend/app/main.py`, `frontend/src/lib/api.ts`,
  `frontend/src/components/FilterBar.tsx`
