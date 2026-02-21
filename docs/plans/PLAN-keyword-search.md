# Implementation Plan: Full-Text Keyword Search

> Spec: [docs/specs/keyword-search.md](../specs/keyword-search.md) | Date: 2026-02-21 | Status: Ready

## Overview

Adds an optional `q` query parameter to `GET /api/writeups` that performs a case-insensitive
substring match against `title` and `summary` via PostgREST's `or=` filter. On the frontend,
`FilterBar` gains a `TextInput` that submits on Enter, `WriteupFilters` gains a `q` field,
and `App.tsx` renders an empty-state message when a search returns no results.

**Files affected:** `backend/app/main.py`, `backend/tests/test_api.py`,
`frontend/src/lib/api.ts`, `frontend/src/hooks/useWriteups.ts`,
`frontend/src/components/FilterBar.tsx`, `frontend/src/App.tsx`

## Tech Stack & Conventions

- **Framework:** React 19 + Vite + TypeScript (frontend), FastAPI (backend)
- **State management:** `useState` in `App.tsx`, passed as props — no global store
- **API pattern:** `fetch` in `lib/api.ts` → TanStack Query hook → `App.tsx`
- **UI components:** Mantine v8 (`@mantine/core`, already installed)
- **Testing:** Python `unittest` with `fastapi.testclient.TestClient` for API tests
- **Key convention source:** CLAUDE.md + code

## Architecture Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| `initialFilters` duplication | Consolidate to `lib/api.ts`, import from both `App.tsx` and `FilterBar.tsx` | Removes silent drift risk when new fields are added in future |

## File Changes

### New Files

None.

### Modified Files

- `backend/app/main.py` — add `q` param, sanitization helper, PostgREST `or=` filter
- `backend/tests/test_api.py` — add tests for `q` parameter behavior
- `frontend/src/lib/api.ts` — add `q: string` to `WriteupFilters`, export `initialFilters`, pass `q` in `fetchWriteups`
- `frontend/src/hooks/useWriteups.ts` — add `q` to TanStack Query key
- `frontend/src/components/FilterBar.tsx` — add `TextInput`, local input state, Enter handler, `useEffect` sync, import `initialFilters`
- `frontend/src/App.tsx` — import `initialFilters`, add `showSearchEmpty` condition + empty-state UI

## Implementation Tasks

Work through phases in order — each is independently testable before moving on.

### Phase 1: Backend — `backend/app/main.py`

- [ ] Add a `_sanitize_q(q: str) -> str` helper at module level that strips `*`, `(`, `)`, `,`
  and trims whitespace. Example: `re.sub(r'[*(,)]', '', q).strip()`
- [ ] Add `q: str | None = Query(default=None)` to `list_writeups` signature
- [ ] After the existing `year`/`month` filter block and before `order=`, add:
  ```python
  if q:
      sanitized = _sanitize_q(q)
      if sanitized:
          filters.append(
              f"or=(title.ilike.*{sanitized}*,summary.ilike.*{sanitized}*)"
          )
  ```
- [ ] Verify manually: `GET /api/writeups?q=SSRF` produces a URL with the `or=` clause

### Phase 2: Backend tests — `backend/tests/test_api.py`

- [ ] Add a test class (also guarded by `@unittest.skipUnless(FASTAPI_INSTALLED, ...)`) with:
  - `test_list_writeups_q_builds_or_filter` — mock `requests.get`, call
    `GET /api/writeups?q=SSRF`, assert the captured URL contains
    `or=(title.ilike.*SSRF*,summary.ilike.*SSRF*)`
  - `test_list_writeups_q_sanitizes_special_chars` — call with `q=SS*RF(bad)`,
    assert URL contains `*SSRF bad*` (special chars stripped)
  - `test_list_writeups_q_absent_skips_or_filter` — call without `q`,
    assert URL does **not** contain `or=`
- [ ] Run `npm run backend:test` — all tests pass

### Phase 3: Frontend types — `frontend/src/lib/api.ts`

- [ ] Add `q: string` to the `WriteupFilters` type
- [ ] Add and export `initialFilters`:
  ```ts
  export const initialFilters: WriteupFilters = {
    source: 'all',
    year: '',
    month: '',
    favorites: false,
    q: '',
  }
  ```
- [ ] In `fetchWriteups`, add `if (filters.q) params.set('q', filters.q)` after the
  existing `month` param block

### Phase 4: Frontend hook — `frontend/src/hooks/useWriteups.ts`

- [ ] Add `filters.q` to the `queryKey` array so different searches are cached separately:
  ```ts
  queryKey: ['writeups', filters.source, filters.year, filters.month, filters.q],
  ```

### Phase 5: Frontend FilterBar — `frontend/src/components/FilterBar.tsx`

- [ ] Add `TextInput` to the Mantine import line
- [ ] Add `useState` import from React
- [ ] Remove the local `initialFilters` constant; import `initialFilters` from `'../lib/api'`
- [ ] Add local state: `const [inputValue, setInputValue] = useState(filters.q)`
- [ ] Add a `useEffect` to sync local input when the parent resets `q` (e.g. "Limpar busca"
  button in `App.tsx`):
  ```ts
  useEffect(() => {
    if (filters.q === '') setInputValue('')
  }, [filters.q])
  ```
- [ ] Add `TextInput` **before** the existing `Select` group inside `.filters-grid`:
  ```tsx
  <TextInput
    label="Buscar"
    placeholder="Título ou resumo…"
    value={inputValue}
    onChange={(e) => setInputValue(e.currentTarget.value)}
    onKeyDown={(e) => {
      if (e.key !== 'Enter') return
      const trimmed = inputValue.trim()
      onChange({ ...filters, q: trimmed })
    }}
  />
  ```
- [ ] Update the "Limpar filtros" `onClick` so it also resets local input:
  ```tsx
  onClick={() => {
    setInputValue('')
    onChange(initialFilters)
  }}
  ```

### Phase 6: Frontend App.tsx — `frontend/src/App.tsx`

- [ ] Remove the local `initialFilters` constant; import `initialFilters` from `'./lib/api'`
  (note: `WriteupFilters` is already imported from `'./lib/api'` — `initialFilters` joins it)
- [ ] Add `showSearchEmpty` condition after `showFavoritesEmpty`:
  ```ts
  const showSearchEmpty = !isPending && !error && filtered.length === 0 && !!filters.q
  ```
- [ ] In the JSX, after the favorites empty-state `<Text>`, add the search empty-state:
  ```tsx
  {showSearchEmpty ? (
    <Stack align="flex-start" gap="xs">
      <Text size="sm" c="dimmed">
        Nenhum writeup encontrado para "{filters.q}". Tente outros termos ou limpe a busca.
      </Text>
      <Button
        variant="light"
        radius="md"
        size="xs"
        onClick={() => setFilters({ ...filters, q: '' })}
      >
        Limpar busca
      </Button>
    </Stack>
  ) : null}
  ```
- [ ] Update the guard on the results grid to also exclude the search empty state:
  ```tsx
  {!isPending && !error && !showFavoritesEmpty && !showSearchEmpty ? (
  ```
- [ ] Add `Button` to Mantine imports (if not already present)

### Phase 7: Acceptance criteria verification

Run through these manually (or with `npm run check`):

- [ ] Type "SSRF" in the search box, press Enter → network request includes `?q=SSRF`
- [ ] API response contains only writeups whose title or summary includes "ssrf"
- [ ] Combine with `source=hackerone` → only HackerOne results containing query
- [ ] Enter whitespace only, press Enter → no new API request; q remains `''`
- [ ] Enter a query with `*` or `(` → URL shows the stripped version
- [ ] No results case → empty-state message + "Limpar busca" button appear
- [ ] Clicking "Limpar busca" → search input cleared, full results reload
- [ ] Clicking "Limpar filtros" → all dropdowns reset AND search input cleared

## Security Considerations

The `q` value is interpolated directly into a PostgREST `or=` filter string. Without
sanitization, characters `*`, `(`, `)`, `,` could escape the `ilike` value and inject
additional filter clauses (PostgREST filter injection). Mitigation: `_sanitize_q` strips
those characters server-side before interpolation — addressed in Phase 1. No SQL injection
risk (PostgREST handles parameterization internally). No XSS (results rendered as text).
No auth changes required.
