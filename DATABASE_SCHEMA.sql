-- Database Schema Setup for Job Hub

-- This document contains the complete SQL schema for the Job Hub application with three normalized tables: `job_applications`, `application_events`, and `emails`.

-- 1. Create Custom Enum Types

-- First, create the custom enum types for application status and event types:

-- Create application status enum
CREATE TYPE application_status AS ENUM (
  'APPLIED',
  'ASSESSMENT',
  'INTERVIEW',
  'REJECTED',
  'OFFERED',
  'ACCEPTED',
  'WITHDRAWN'
);

-- Create application event type enum
CREATE TYPE application_event_type AS ENUM (
  'APPLICATION_SUBMITTED',
  'APPLICATION_RECEIVED',
  'APPLICATION_VIEWED',
  'APPLICATION_REVIEWED',
  'ASSESSMENT_RECEIVED',
  'ASSESSMENT_COMPLETED',
  'INTERVIEW_SCHEDULED',
  'INTERVIEW_COMPLETED',
  'FINAL_ROUND',
  'REFERENCE_REQUESTED',
  'OFFER_RECEIVED',
  'OFFER_ACCEPTED',
  'OFFER_DECLINED',
  'APPLICATION_REJECTED',
  'APPLICATION_WITHDRAWN'
);

-- Create application source type enum
CREATE TYPE application_source_type AS ENUM (
  'EMAIL',
  'LINKEDIN_EASY_APPLY'
);

-- Create application merge status enum
CREATE TYPE application_merge_status AS ENUM (
  'AUTO_MERGED',
  'PENDING_REVIEW',
  'UNMATCHED',
  'MANUALLY_CONFIRMED',
  'MANUALLY_SEPARATED'
);

-- 2. Create Tables

-- Job Applications Table

-- Create or replace job_applications table
DROP TABLE IF EXISTS job_applications CASCADE;
CREATE TABLE job_applications (
application_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
user_id TEXT NOT NULL,
company TEXT NOT NULL,
role TEXT NOT NULL,
status application_status NOT NULL,
job_posting_url TEXT,
location TEXT,
salary_range TEXT,
notes TEXT,
applied_date TIMESTAMPTZ,
canonical_source TEXT,
application_origin TEXT,
application_inferred BOOLEAN DEFAULT FALSE,
inferred_reason TEXT,
applied_date_precision TEXT,
match_confidence FLOAT,
needs_review BOOLEAN DEFAULT FALSE,
created_at TIMESTAMPTZ DEFAULT now(),
last_updated_at TIMESTAMPTZ, -- No default, will be NULL initially
last_email_received_at TIMESTAMPTZ -- Track last email specifically
);

-- Create or replace application_events table
DROP TABLE IF EXISTS application_events CASCADE;
CREATE TABLE application_events (
event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
application_id UUID NOT NULL REFERENCES job_applications(application_id) ON DELETE CASCADE,
user_id TEXT NOT NULL,
event_type application_event_type NOT NULL,
event_date TIMESTAMPTZ NOT NULL,
description TEXT,
location TEXT,
contact_person TEXT,
notes TEXT,
email_id UUID, -- Reference to triggering email if applicable
source_type application_source_type,
source_id UUID,
is_inferred BOOLEAN DEFAULT FALSE,
confidence_score FLOAT,
created_at TIMESTAMPTZ DEFAULT now()
);

-- Create or replace emails table
DROP TABLE IF EXISTS emails CASCADE;
CREATE TABLE emails (
email_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
user_id TEXT NOT NULL,
application_id UUID REFERENCES job_applications(application_id) ON DELETE SET NULL,
external_email_id TEXT NOT NULL,
sender TEXT NOT NULL,
recipient TEXT NOT NULL,
subject TEXT NOT NULL,
body_text TEXT,
body_html TEXT,
received_at TIMESTAMPTZ NOT NULL,
parsed_at TIMESTAMPTZ,
confidence_score FLOAT,
created_at TIMESTAMPTZ DEFAULT now()
);

-- Create application_sources table for raw email and LinkedIn records
DROP TABLE IF EXISTS application_sources CASCADE;
CREATE TABLE application_sources (
source_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
user_id TEXT NOT NULL,
source_type application_source_type NOT NULL,
external_source_id TEXT,
application_id UUID REFERENCES job_applications(application_id) ON DELETE SET NULL,
candidate_application_id UUID REFERENCES job_applications(application_id) ON DELETE SET NULL,
company_raw TEXT NOT NULL,
role_raw TEXT NOT NULL,
applied_at TIMESTAMPTZ,
observed_at TIMESTAMPTZ,
sender_domain TEXT,
source_url TEXT,
payload_json JSONB,
merge_confidence FLOAT,
merge_status application_merge_status NOT NULL DEFAULT 'UNMATCHED',
review_reason TEXT,
created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS application_sources_user_id_idx ON application_sources(user_id);
CREATE INDEX IF NOT EXISTS application_sources_application_id_idx ON application_sources(application_id);
CREATE INDEX IF NOT EXISTS application_sources_candidate_application_id_idx ON application_sources(candidate_application_id);
CREATE INDEX IF NOT EXISTS application_sources_merge_status_idx ON application_sources(merge_status);

-- Create email_refs table used by the backend email pipeline
DROP TABLE IF EXISTS email_refs CASCADE;
CREATE TABLE email_refs (
email_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
user_id TEXT NOT NULL,
application_id UUID REFERENCES job_applications(application_id) ON DELETE SET NULL,
external_email_id TEXT NOT NULL,
thread_id TEXT,
history_id BIGINT,
received_at TIMESTAMPTZ NOT NULL,
created_at TIMESTAMPTZ DEFAULT now()
);

-- Add index on user_id for all tables
CREATE INDEX IF NOT EXISTS job_applications_user_id_idx ON job_applications(user_id);
CREATE INDEX IF NOT EXISTS application_events_user_id_idx ON application_events(user_id);
CREATE INDEX IF NOT EXISTS emails_user_id_idx ON emails(user_id);

-- Add index on application_id for related tables
CREATE INDEX IF NOT EXISTS application_events_application_id_idx ON application_events(application_id);
CREATE INDEX IF NOT EXISTS emails_application_id_idx ON emails(application_id);

-- Add index on last_updated_at for sorting applications by recency
CREATE INDEX IF NOT EXISTS job_applications_last_updated_at_idx ON job_applications(last_updated_at);

CREATE OR REPLACE FUNCTION update_job_application_timestamp()
RETURNS TRIGGER AS $$
BEGIN
-- Only set last_updated_at when a record is being updated, not created
IF TG_OP = 'UPDATE' THEN
NEW.last_updated_at = now();
END IF;
RETURN NEW;
END;

$$
LANGUAGE plpgsql;

-- Apply to both INSERT and UPDATE operations
CREATE TRIGGER update_job_application_timestamp
BEFORE UPDATE ON job_applications
FOR EACH ROW
EXECUTE FUNCTION update_job_application_timestamp();

-- Create trigger function to update last_email_received_at and last_updated_at when a new email is inserted
CREATE OR REPLACE FUNCTION update_job_application_on_email_insert()
RETURNS TRIGGER AS
$$

BEGIN
IF NEW.application_id IS NOT NULL THEN
UPDATE job_applications
SET
last_email_received_at = NEW.received_at,
last_updated_at = now()
WHERE application_id = NEW.application_id;
END IF;
RETURN NEW;
END;

$$
LANGUAGE plpgsql;

-- Create trigger to update job_applications when a new email is inserted
CREATE TRIGGER update_job_application_on_email_insert
AFTER INSERT ON emails
FOR EACH ROW
EXECUTE FUNCTION update_job_application_on_email_insert();

-- Update RLS policies for all tables
ALTER TABLE job_applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_refs ENABLE ROW LEVEL SECURITY;

-- Development policies (remove in production)
CREATE POLICY "dev_job_applications_policy" ON job_applications FOR ALL USING (true);
CREATE POLICY "dev_application_events_policy" ON application_events FOR ALL USING (true);
CREATE POLICY "dev_emails_policy" ON emails FOR ALL USING (true);
CREATE POLICY "dev_application_sources_policy" ON application_sources FOR ALL USING (true);
CREATE POLICY "dev_email_refs_policy" ON email_refs FOR ALL USING (true);
$$
