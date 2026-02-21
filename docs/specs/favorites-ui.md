# Spec: Favorites UI

> Status: Draft | Linear: N/A | Date: 2026-02-21

## Problem Statement

Users of the bug bounty writeups aggregator have no way to mark writeups as favorites. The database already has a `preserve_favorites` column and a cleanup job that respects it, but the frontend never exposes the field — leaving the feature half-built and favorites permanently exposed to deletion by the scraper.

## Goals

- Users can star/unstar any writeup from the grid; the state persists in Supabase via the backend.
- Users can filter the grid to show only favorited writeups.
- Favorites survive page reload with no extra action from the user.

## Non-Goals (Out of Scope)

- Per-user favorites — favorites are shared across all users of the instance (no authentication).
- Bulk favorite/unfavorite operations.
- Notifications or alerts based on favorites.
- Changes to the cleanup job itself — it already honors `preserve_favorites`.

## User Stories

- As a user, I want to star a writeup card so that it is saved as a favorite and protected from cleanup.
- As a user, I want to click the star again to un-favorite a writeup, so that I can manage the list.
- As a user, I want a "Favorites only" toggle in the filter bar so that I can view only saved writeups.
- As a user, I want my favorites to persist on page reload so that the list is durable.

## Functional Requirements

- `GET /api/writeups` must include `preserve_favorites` in its Supabase `select` clause so the frontend receives the field.
- A new `PATCH /api/writeups/{id}` endpoint must accept `{ "preserve_favorites": true | false }` and update the row in Supabase.
- `WriteupCard` must display a star icon button (top-right corner of the card):
  - Filled/active when `preserve_favorites` is `true`; outlined when `false`.
  - Clicking the star calls the PATCH endpoint and toggles the state.
  - The button must call `e.stopPropagation()` and `e.preventDefault()` so it does not follow the card's `<a>` link.
- `FilterBar` must include a "Favorites only" toggle:
  - When active, only writeups where `preserve_favorites === true` are displayed.
  - Filtering is client-side — all writeups are loaded in a single request.
- Toggle behavior is optimistic: the UI updates immediately; on PATCH failure, the star reverts and an error is shown.

## Acceptance Criteria

- [ ] A star icon appears on every writeup card.
- [ ] Clicking the star on an un-favorited writeup fills the star and sets `preserve_favorites = true` in Supabase.
- [ ] Clicking the star on a favorited writeup unfills it and sets `preserve_favorites = false`.
- [ ] Reloading the page shows the same starred writeups as before.
- [ ] Clicking the star does not navigate away from the page.
- [ ] The "Favorites only" toggle in `FilterBar` hides all non-favorited writeups.
- [ ] When "Favorites only" is active and there are no favorites, an empty-state message is shown.

## Edge Cases & Error States

- **PATCH fails** (network error or 502): star reverts to its pre-click state; show a brief error (Mantine `notifications` or inline indicator).
- **Empty favorites state**: When "Favorites only" is on and no writeups are favorited, show: *"Nenhum favorito ainda. Clique na estrela de um writeup para salvá-lo."*
- **Star clicked while request is in-flight**: disable the star button until the PATCH settles to prevent double-toggling.
- **`preserve_favorites` absent in API response** (stale cache or type mismatch): treat as `false`.

## Technical Constraints

- `backend/app/main.py` — update the `select=` query string to add `preserve_favorites`; add the new `PATCH /api/writeups/{id}` endpoint (proxies to Supabase REST via `requests.patch`, same credentials pattern as the existing GET).
- `frontend/src/lib/api.ts` — add `preserve_favorites: boolean` to the `Writeup` type; add a `favorites: boolean` field to `WriteupFilters`; add a `patchFavorite(id: string, value: boolean): Promise<void>` function.
- `frontend/src/components/WriteupCard.tsx` — the entire card is an `<a>` tag; the star `ActionIcon` must stop event propagation.
- `@tabler/icons-react` is **not currently installed** — it must be added as a dependency (standard companion for Mantine) to use `IconStar` / `IconStarFilled`, or a simpler inline SVG/Unicode approach can be substituted.

## Open Questions

None — all questions resolved before writing.

## Minor Assumptions

- Empty-state copy is in Portuguese to match the existing UI language.
- Optimistic UI is preferred over a loading spinner on the star button.
- `@tabler/icons-react` is the assumed icon source; can be swapped for inline SVG with no functional impact.

## References

- Linear: N/A
- Feature ideas file: `docs/plans/2026-02-21-feature-ideas.md` — item #1
- Related files: `backend/app/main.py`, `frontend/src/components/WriteupCard.tsx`, `frontend/src/components/FilterBar.tsx`, `frontend/src/lib/api.ts`
