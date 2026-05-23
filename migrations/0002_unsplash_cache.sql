-- 0002_unsplash_cache.sql
create table unsplash_cache (
  query        text primary key,
  photo_id     text not null,
  urls         jsonb not null,
  attribution_html text not null,
  page_url     text not null,
  fetched_at   timestamptz not null default now()
);

create index unsplash_cache_fetched_idx on unsplash_cache(fetched_at);
