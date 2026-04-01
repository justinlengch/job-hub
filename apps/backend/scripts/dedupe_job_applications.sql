-- Conservative cleanup for duplicate job_applications rows.
--
-- What it does:
-- 1. Finds duplicate application groups for the same user where the rows are
--    effectively identical:
--      - same normalized company
--      - same normalized role
--      - same normalized job_posting_url
--      - same normalized location
--      - same applied_date day
-- 2. Keeps one canonical application per group.
-- 3. Repoints dependent rows in:
--      - application_events.application_id
--      - email_refs.application_id
--      - application_sources.application_id
--      - application_sources.candidate_application_id
-- 4. Deletes the extra job_applications rows.
--
-- Important:
-- - Review the preview query first.
-- - This script is intentionally conservative. It will not merge looser
--   "probably the same job" rows.
-- - Run in Supabase SQL editor or psql.

-- Preview duplicate groups first.
with normalized as (
  select
    application_id,
    user_id,
    lower(trim(company)) as company_key,
    lower(trim(role)) as role_key,
    coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__') as url_key,
    coalesce(nullif(lower(trim(location)), ''), '__null__') as location_key,
    coalesce(applied_date::date::text, '__null__') as applied_day_key,
    created_at
  from public.job_applications
),
dupe_groups as (
  select
    user_id,
    company_key,
    role_key,
    url_key,
    location_key,
    applied_day_key,
    count(*) as duplicate_count,
    min(created_at) as first_created_at
  from normalized
  group by 1, 2, 3, 4, 5, 6
  having count(*) > 1
)
select *
from dupe_groups
order by duplicate_count desc, first_created_at asc;

-- Uncomment this block to perform the cleanup.
/*
begin;

with normalized as (
  select
    application_id,
    user_id,
    lower(trim(company)) as company_key,
    lower(trim(role)) as role_key,
    coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__') as url_key,
    coalesce(nullif(lower(trim(location)), ''), '__null__') as location_key,
    coalesce(applied_date::date::text, '__null__') as applied_day_key,
    created_at,
    row_number() over (
      partition by
        user_id,
        lower(trim(company)),
        lower(trim(role)),
        coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__'),
        coalesce(nullif(lower(trim(location)), ''), '__null__'),
        coalesce(applied_date::date::text, '__null__')
      order by created_at asc, application_id asc
    ) as rn,
    first_value(application_id) over (
      partition by
        user_id,
        lower(trim(company)),
        lower(trim(role)),
        coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__'),
        coalesce(nullif(lower(trim(location)), ''), '__null__'),
        coalesce(applied_date::date::text, '__null__')
      order by created_at asc, application_id asc
    ) as keep_application_id
  from public.job_applications
),
dupes as (
  select
    application_id as duplicate_application_id,
    keep_application_id
  from normalized
  where rn > 1
)
update public.application_events e
set application_id = d.keep_application_id
from dupes d
where e.application_id = d.duplicate_application_id;

with normalized as (
  select
    application_id,
    user_id,
    lower(trim(company)) as company_key,
    lower(trim(role)) as role_key,
    coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__') as url_key,
    coalesce(nullif(lower(trim(location)), ''), '__null__') as location_key,
    coalesce(applied_date::date::text, '__null__') as applied_day_key,
    created_at,
    row_number() over (
      partition by
        user_id,
        lower(trim(company)),
        lower(trim(role)),
        coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__'),
        coalesce(nullif(lower(trim(location)), ''), '__null__'),
        coalesce(applied_date::date::text, '__null__')
      order by created_at asc, application_id asc
    ) as rn,
    first_value(application_id) over (
      partition by
        user_id,
        lower(trim(company)),
        lower(trim(role)),
        coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__'),
        coalesce(nullif(lower(trim(location)), ''), '__null__'),
        coalesce(applied_date::date::text, '__null__')
      order by created_at asc, application_id asc
    ) as keep_application_id
  from public.job_applications
),
dupes as (
  select
    application_id as duplicate_application_id,
    keep_application_id
  from normalized
  where rn > 1
)
update public.email_refs r
set application_id = d.keep_application_id
from dupes d
where r.application_id = d.duplicate_application_id;

with normalized as (
  select
    application_id,
    user_id,
    lower(trim(company)) as company_key,
    lower(trim(role)) as role_key,
    coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__') as url_key,
    coalesce(nullif(lower(trim(location)), ''), '__null__') as location_key,
    coalesce(applied_date::date::text, '__null__') as applied_day_key,
    created_at,
    row_number() over (
      partition by
        user_id,
        lower(trim(company)),
        lower(trim(role)),
        coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__'),
        coalesce(nullif(lower(trim(location)), ''), '__null__'),
        coalesce(applied_date::date::text, '__null__')
      order by created_at asc, application_id asc
    ) as rn,
    first_value(application_id) over (
      partition by
        user_id,
        lower(trim(company)),
        lower(trim(role)),
        coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__'),
        coalesce(nullif(lower(trim(location)), ''), '__null__'),
        coalesce(applied_date::date::text, '__null__')
      order by created_at asc, application_id asc
    ) as keep_application_id
  from public.job_applications
),
dupes as (
  select
    application_id as duplicate_application_id,
    keep_application_id
  from normalized
  where rn > 1
)
update public.application_sources s
set application_id = d.keep_application_id
from dupes d
where s.application_id = d.duplicate_application_id;

with normalized as (
  select
    application_id,
    user_id,
    lower(trim(company)) as company_key,
    lower(trim(role)) as role_key,
    coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__') as url_key,
    coalesce(nullif(lower(trim(location)), ''), '__null__') as location_key,
    coalesce(applied_date::date::text, '__null__') as applied_day_key,
    created_at,
    row_number() over (
      partition by
        user_id,
        lower(trim(company)),
        lower(trim(role)),
        coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__'),
        coalesce(nullif(lower(trim(location)), ''), '__null__'),
        coalesce(applied_date::date::text, '__null__')
      order by created_at asc, application_id asc
    ) as rn,
    first_value(application_id) over (
      partition by
        user_id,
        lower(trim(company)),
        lower(trim(role)),
        coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__'),
        coalesce(nullif(lower(trim(location)), ''), '__null__'),
        coalesce(applied_date::date::text, '__null__')
      order by created_at asc, application_id asc
    ) as keep_application_id
  from public.job_applications
),
dupes as (
  select
    application_id as duplicate_application_id,
    keep_application_id
  from normalized
  where rn > 1
)
update public.application_sources s
set candidate_application_id = d.keep_application_id
from dupes d
where s.candidate_application_id = d.duplicate_application_id;

with normalized as (
  select
    application_id,
    user_id,
    lower(trim(company)) as company_key,
    lower(trim(role)) as role_key,
    coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__') as url_key,
    coalesce(nullif(lower(trim(location)), ''), '__null__') as location_key,
    coalesce(applied_date::date::text, '__null__') as applied_day_key,
    created_at,
    row_number() over (
      partition by
        user_id,
        lower(trim(company)),
        lower(trim(role)),
        coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__'),
        coalesce(nullif(lower(trim(location)), ''), '__null__'),
        coalesce(applied_date::date::text, '__null__')
      order by created_at asc, application_id asc
    ) as rn
  from public.job_applications
)
delete from public.job_applications a
using normalized n
where a.application_id = n.application_id
  and n.rn > 1;

commit;
*/
