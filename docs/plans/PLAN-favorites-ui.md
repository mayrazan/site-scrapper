# Implementation Plan: Favorites UI

> Spec: [docs/specs/favorites-ui.md](../specs/favorites-ui.md) | Date: 2026-02-21 | Status: Ready

## Overview

Implements star/unstar on every WriteupCard backed by a new `PATCH /api/writeups/{id}` FastAPI
endpoint that proxies to Supabase. Favorites state is already stored in `preserve_favorites` on
the DB row; this plan surfaces it end-to-end. A "Somente favoritos" Switch in FilterBar provides
client-side filtering. UI updates are optimistic; PATCH failures revert the star and show a
`@mantine/notifications` toast.

---

## Tech Stack & Conventions

| Concern | Approach | Example file |
|---|---|---|
| Framework | React 19 + TypeScript + Vite | `frontend/src/main.tsx` |
| UI library | Mantine v8 | `frontend/src/components/FilterBar.tsx` |
| Server state | TanStack Query v5 | `frontend/src/hooks/useWriteups.ts` |
| Local/optimistic state | `useState` in component | `frontend/src/components/WriteupCard.tsx` |
| API proxy | FastAPI → Supabase REST via `requests` | `backend/app/main.py` |
| UI language | Portuguese | all UI files |

---

## New Dependencies

| Package | Version | Purpose |
|---|---|---|
| `@mantine/notifications` | ^8.x (match existing `@mantine/core`) | Toast notifications for PATCH errors |

> Install: `npm install @mantine/notifications` inside `frontend/`

---

## Architecture Decisions

| Decision | Choice | Reason |
|---|---|---|
| Star icon source | Inline SVG (no new icon package) | Zero extra dependency |
| Error feedback | `@mantine/notifications` toast | User-selected; best UX |
| Filter toggle UI | Mantine `Switch` | User-selected; clear on/off semantics |
| Favorites filtering | Client-side in App.tsx | All writeups already fetched in one request |
| Optimistic state | `useState` inside `WriteupCard` | Self-contained per card; no React Query mutation needed |
| PATCH ID validation | FastAPI `UUID` path type | Prevents path injection before proxying |

---

## File Changes

### Modified Files

- `backend/app/main.py` — add `preserve_favorites` to `select=` clause; add `PATCH /api/writeups/{writeup_id}` endpoint
- `frontend/src/lib/api.ts` — add `preserve_favorites` field to `Writeup` type; add `favorites` field to `WriteupFilters`; add `patchFavorite()` function
- `frontend/src/components/WriteupCard.tsx` — add star `ActionIcon` with inline SVG, optimistic state, and error handling
- `frontend/src/components/FilterBar.tsx` — add `Switch` for "Somente favoritos"; update `initialFilters`
- `frontend/src/App.tsx` — add `favorites: false` to `initialFilters`; add client-side favorites filter; add empty-state for no favorites
- `frontend/src/main.tsx` — import `@mantine/notifications/styles.css`; render `<Notifications />` inside `MantineProvider`

---

## Implementation Tasks

### Phase 1 — Backend

- [ ] In `main.py` line 39, change the `select=` filter from:
  ```
  "select=id,source,title,url,author,summary,published_at,created_at"
  ```
  to:
  ```
  "select=id,source,title,url,author,summary,published_at,created_at,preserve_favorites"
  ```
- [ ] Add Pydantic model above the route functions:
  ```python
  from pydantic import BaseModel
  from uuid import UUID

  class PatchFavoriteBody(BaseModel):
      preserve_favorites: bool
  ```
- [ ] Add `PATCH /api/writeups/{writeup_id}` endpoint following the same credentials pattern as the GET:
  ```python
  @app.patch("/api/writeups/{writeup_id}", status_code=204)
  def patch_favorite(writeup_id: UUID, body: PatchFavoriteBody) -> None:
      if not settings.supabase_url or not settings.supabase_service_key:
          raise HTTPException(status_code=500, detail="Missing Supabase credentials")
      endpoint = f"{settings.supabase_url}/rest/v1/writeups?id=eq.{writeup_id}"
      headers = {
          "apikey": settings.supabase_service_key,
          "Authorization": f"Bearer {settings.supabase_service_key}",
          "Content-Type": "application/json",
          "Prefer": "return=minimal",
      }
      try:
          response = requests.patch(endpoint, headers=headers, json={"preserve_favorites": body.preserve_favorites}, timeout=30)
          response.raise_for_status()
      except requests.RequestException as exc:
          raise HTTPException(status_code=502, detail=f"Supabase update failed: {exc}") from exc
  ```

---

### Phase 2 — Frontend: API layer (`frontend/src/lib/api.ts`)

- [ ] Add `preserve_favorites: boolean` to the `Writeup` type
- [ ] Add `favorites: boolean` to the `WriteupFilters` type
- [ ] Add `patchFavorite` function (does NOT affect `fetchWriteups`; `favorites` is client-side only):
  ```ts
  export async function patchFavorite(id: string, value: boolean): Promise<void> {
    const response = await fetch(`${API_BASE}/api/writeups/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preserve_favorites: value }),
    })
    if (!response.ok) throw new Error(`Falha ao atualizar favorito: ${response.status}`)
  }
  ```

---

### Phase 3 — Frontend: Notifications setup (`frontend/src/main.tsx`)

- [ ] Add import at top: `import '@mantine/notifications/styles.css'`
- [ ] Add import: `import { Notifications } from '@mantine/notifications'`
- [ ] Render `<Notifications />` as first child inside `<MantineProvider>` (before `QueryClientProvider`)

---

### Phase 4 — Frontend: Star button (`frontend/src/components/WriteupCard.tsx`)

- [ ] Import `ActionIcon` from `@mantine/core`; import `notifications` from `@mantine/notifications`; import `useState` from `react`; import `patchFavorite` from `../lib/api`
- [ ] Add local state inside the component:
  ```ts
  const [isFavorite, setIsFavorite] = useState(item.preserve_favorites ?? false)
  const [isLoading, setIsLoading] = useState(false)
  ```
- [ ] Add async toggle handler:
  ```ts
  async function handleToggleFavorite(e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    if (isLoading) return
    const next = !isFavorite
    setIsFavorite(next)
    setIsLoading(true)
    try {
      await patchFavorite(item.id, next)
    } catch {
      setIsFavorite(!next)
      notifications.show({ color: 'red', message: 'Erro ao salvar favorito.' })
    } finally {
      setIsLoading(false)
    }
  }
  ```
- [ ] In the existing `<Group justify="space-between" align="start">` (currently holds Badge and date Text), add an `ActionIcon` on the right edge:
  ```tsx
  <ActionIcon
    variant="transparent"
    size="sm"
    disabled={isLoading}
    onClick={handleToggleFavorite}
    aria-label={isFavorite ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
    c={isFavorite ? 'yellow' : 'gray'}
  >
    {isFavorite ? (
      /* filled star SVG */
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
      </svg>
    ) : (
      /* outlined star SVG */
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
      </svg>
    )}
  </ActionIcon>
  ```

---

### Phase 5 — Frontend: FilterBar switch (`frontend/src/components/FilterBar.tsx`)

- [ ] Import `Switch` from `@mantine/core`
- [ ] Add `favorites: false` to the `initialFilters` constant
- [ ] Add `<Switch>` below the `<div className="filters-grid">`, before the reset `<Group>`:
  ```tsx
  <Switch
    label="Somente favoritos"
    checked={filters.favorites}
    onChange={(e) => onChange({ ...filters, favorites: e.currentTarget.checked })}
    mt="sm"
  />
  ```
- [ ] Ensure the existing `onChange(initialFilters)` in "Limpar filtros" resets `favorites` to `false` (it will, since `initialFilters` now includes it)

---

### Phase 6 — Frontend: Client-side filtering (`frontend/src/App.tsx`)

- [ ] Add `favorites: false` to `initialFilters`
- [ ] After the `sorted` useMemo, add a `filtered` useMemo:
  ```ts
  const filtered = useMemo(
    () => (filters.favorites ? sorted.filter((item) => item.preserve_favorites) : sorted),
    [sorted, filters.favorites],
  )
  ```
- [ ] Replace all references to `sorted` in the JSX render with `filtered` (result count text and `SimpleGrid` map)
- [ ] Add empty-state for no favorites: when `!isPending && !error && filtered.length === 0 && filters.favorites`:
  ```tsx
  <Text size="sm" c="dimmed">
    Nenhum favorito ainda. Clique na estrela de um writeup para salvá-lo.
  </Text>
  ```

---

## Security Considerations

- **Path injection prevention**: Using `UUID` as the FastAPI path type auto-validates format before the value is interpolated into the Supabase URL (`id=eq.{writeup_id}`). Invalid UUIDs get a 422 from FastAPI without hitting Supabase.
- **Body validation**: Pydantic `PatchFavoriteBody` enforces `preserve_favorites: bool` — no unexpected payload types reach Supabase.
- **No auth surface change**: Feature is consistent with the existing shared-instance, no-authentication model stated in the spec.
- **No SQL injection surface**: Supabase REST uses equality operators (`id=eq.{uuid}`) on a validated UUID; no user-controlled string is concatenated into a filter expression.

---

## Verification

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. `GET /api/writeups` — confirm each row includes `preserve_favorites`
3. `PATCH /api/writeups/{valid-id}` with `{"preserve_favorites": true}` — expect `204`
4. `PATCH /api/writeups/not-a-uuid` — expect `422`
5. Start frontend: `cd frontend && npm run dev`
6. Verify star icon appears on every card (outlined by default)
7. Click a star → fills immediately (optimistic), reload → still filled
8. Click filled star → unfills, reload → unfilled
9. Enable "Somente favoritos" Switch → only starred cards visible
10. Enable "Somente favoritos" with zero starred cards → empty-state message shown
11. "Limpar filtros" → Switch resets, all cards visible
12. Force PATCH error (temporarily break `VITE_API_BASE_URL`) → star reverts, red toast appears
