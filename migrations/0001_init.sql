-- 0001_init.sql
create extension if not exists "pgcrypto";

create table submissions (
  id            uuid primary key default gen_random_uuid(),
  created_at    timestamptz not null default now(),
  full_name     text not null,
  email         text not null,
  brand_name    text not null,
  industry      text not null,
  questionnaire jsonb not null default '{}'::jsonb,
  ip            inet,
  user_agent    text,
  request_hash  text unique
);

create index submissions_email_idx on submissions(email, created_at desc);

create table jobs (
  id                 uuid primary key default gen_random_uuid(),
  submission_id      uuid not null references submissions(id) on delete cascade,
  status             text not null default 'queued',
  progress_pct       int  not null default 0,
  archetype          text,
  slug               text unique,
  palette            jsonb,
  site_url           text,
  error_code         text,
  error_message      text,
  attempts           int  not null default 0,
  claude_tokens_in   int  not null default 0,
  claude_tokens_out  int  not null default 0,
  claude_cost_usd    numeric(10,4) not null default 0,
  created_at         timestamptz not null default now(),
  started_at         timestamptz,
  finished_at        timestamptz,
  constraint jobs_status_chk check (status in (
    'queued','classifying','writing_copy','fetching_images',
    'rendering','publishing','notifying','done','failed'
  ))
);

create index jobs_active_idx
  on jobs(status, created_at)
  where status not in ('done','failed');
create index jobs_submission_idx on jobs(submission_id);
