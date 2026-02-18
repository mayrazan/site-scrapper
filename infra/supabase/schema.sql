-- Extensions
create extension if not exists pgcrypto;

-- Main table
create table if not exists public.writeups (
  id uuid primary key default gen_random_uuid(),
  source text not null check (source in ('portswigger', 'medium', 'hackerone')),
  title text not null,
  url text not null unique,
  author text,
  summary text,
  published_at timestamptz not null,
  created_at timestamptz not null default now(),
  is_favorite boolean not null default false,
  is_read boolean not null default false
);

-- Composite index for source + date filtering/sorting
create index if not exists writeups_source_published_at_idx
  on public.writeups (source, published_at desc);

-- Date index for general sort/filter
create index if not exists writeups_published_at_idx
  on public.writeups (published_at desc);

-- Partial index for favorite fast-filter
create index if not exists writeups_favorites_idx
  on public.writeups (published_at desc)
  where is_favorite = true;

-- RLS
alter table public.writeups enable row level security;

-- Public read-only policy (for anon frontend)
drop policy if exists "writeups_public_read" on public.writeups;
create policy "writeups_public_read"
on public.writeups
for select
to anon, authenticated
using (true);

-- Writes should happen only through service role / backend
drop policy if exists "writeups_no_client_writes" on public.writeups;
create policy "writeups_no_client_writes"
on public.writeups
for all
to anon, authenticated
using (false)
with check (false);

-- Helper view for month/year filtering UI
create or replace view public.writeups_archive as
select
  extract(year from published_at)::int as year,
  extract(month from published_at)::int as month,
  source,
  count(*)::int as total
from public.writeups
group by 1, 2, 3
order by 1 desc, 2 desc;

-- Retention procedure: remove old records, preserve favorites optional
create or replace function public.cleanup_old_writeups(months_to_keep int default 18, preserve_favorites boolean default true)
returns int
language plpgsql
as $$
declare
  deleted_count int;
begin
  if preserve_favorites then
    delete from public.writeups
    where published_at < (now() - make_interval(months => months_to_keep))
      and is_favorite = false;
  else
    delete from public.writeups
    where published_at < (now() - make_interval(months => months_to_keep));
  end if;

  get diagnostics deleted_count = row_count;
  return deleted_count;
end;
$$;
