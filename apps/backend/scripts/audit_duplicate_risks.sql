-- Read-only duplicate/integrity audit for Job Hub tables.
-- Safe to run in Supabase SQL editor.

-- 1. Duplicate email_refs by Gmail message ID
select
  'email_refs' as table_name,
  user_id,
  external_email_id as duplicate_key,
  count(*) as duplicate_count
from public.email_refs
group by 1, 2, 3
having count(*) > 1
order by duplicate_count desc, user_id, duplicate_key;

-- 2. Duplicate email application_sources by email_id-derived external_source_id
select
  'application_sources_email' as table_name,
  user_id,
  external_source_id as duplicate_key,
  count(*) as duplicate_count
from public.application_sources
where source_type = 'EMAIL'
  and external_source_id is not null
group by 1, 2, 3
having count(*) > 1
order by duplicate_count desc, user_id, duplicate_key;

-- 3. Duplicate application_events by source_id
select
  'application_events_source' as table_name,
  null::text as user_id,
  source_id::text as duplicate_key,
  count(*) as duplicate_count
from public.application_events
where source_id is not null
group by 1, 2, 3
having count(*) > 1
order by duplicate_count desc, duplicate_key;

-- 4. Conservative duplicate job_applications candidates
select
  'job_applications_exactish' as table_name,
  user_id,
  concat_ws(
    ' | ',
    lower(trim(company)),
    lower(trim(role)),
    coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__'),
    coalesce(nullif(lower(trim(location)), ''), '__null__'),
    coalesce(applied_date::date::text, '__null__')
  ) as duplicate_key,
  count(*) as duplicate_count
from public.job_applications
group by
  user_id,
  lower(trim(company)),
  lower(trim(role)),
  coalesce(nullif(lower(trim(job_posting_url)), ''), '__null__'),
  coalesce(nullif(lower(trim(location)), ''), '__null__'),
  coalesce(applied_date::date::text, '__null__')
having count(*) > 1
order by duplicate_count desc, user_id, duplicate_key;

-- 5. Queue duplicates by message ID (should be impossible after unique index)
select
  'email_ingest_queue' as table_name,
  user_id,
  external_email_id as duplicate_key,
  count(*) as duplicate_count
from public.email_ingest_queue
group by 1, 2, 3
having count(*) > 1
order by duplicate_count desc, user_id, duplicate_key;

-- 6. Orphaned references: email_refs.application_id missing in job_applications
select
  'orphan_email_refs_application' as issue_type,
  r.email_id::text as row_id,
  r.user_id,
  r.application_id::text as missing_application_id
from public.email_refs r
left join public.job_applications a on a.application_id = r.application_id
where r.application_id is not null
  and a.application_id is null
order by r.user_id, r.email_id;

-- 7. Orphaned references: application_sources.application_id missing
select
  'orphan_application_sources_application' as issue_type,
  s.source_id::text as row_id,
  s.user_id,
  s.application_id::text as missing_application_id
from public.application_sources s
left join public.job_applications a on a.application_id = s.application_id
where s.application_id is not null
  and a.application_id is null
order by s.user_id, s.source_id;

-- 8. Orphaned references: application_sources.candidate_application_id missing
select
  'orphan_application_sources_candidate' as issue_type,
  s.source_id::text as row_id,
  s.user_id,
  s.candidate_application_id::text as missing_application_id
from public.application_sources s
left join public.job_applications a on a.application_id = s.candidate_application_id
where s.candidate_application_id is not null
  and a.application_id is null
order by s.user_id, s.source_id;

-- 9. Orphaned references: application_events.application_id missing
select
  'orphan_application_events_application' as issue_type,
  e.event_id::text as row_id,
  e.user_id,
  e.application_id::text as missing_application_id
from public.application_events e
left join public.job_applications a on a.application_id = e.application_id
where a.application_id is null
order by e.user_id, e.event_id;
