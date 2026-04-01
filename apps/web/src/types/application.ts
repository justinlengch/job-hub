export type ApplicationStatus =
  | "APPLIED"
  | "ASSESSMENT"
  | "INTERVIEW"
  | "REJECTED"
  | "OFFERED"
  | "ACCEPTED"
  | "WITHDRAWN";

export type ApplicationEventType =
  | "APPLICATION_SUBMITTED"
  | "APPLICATION_RECEIVED"
  | "APPLICATION_VIEWED"
  | "APPLICATION_REVIEWED"
  | "ASSESSMENT_RECEIVED"
  | "ASSESSMENT_COMPLETED"
  | "INTERVIEW_SCHEDULED"
  | "INTERVIEW_COMPLETED"
  | "FINAL_ROUND"
  | "REFERENCE_REQUESTED"
  | "OFFER_RECEIVED"
  | "OFFER_ACCEPTED"
  | "OFFER_DECLINED"
  | "APPLICATION_REJECTED"
  | "APPLICATION_WITHDRAWN";

export interface JobApplication {
  id: string;
  user_id: string;
  company: string;
  role: string;
  status: ApplicationStatus;
  job_posting_url?: string;
  location?: string;
  salary_range?: string;
  notes?: string;
  canonical_source?: "EMAIL" | "LINKEDIN" | "MERGED" | "MANUAL";
  application_origin?: "EMAIL" | "LINKEDIN_EASY_APPLY" | "MANUAL" | "UNKNOWN";
  application_inferred?: boolean;
  inferred_reason?: string;
  applied_date_precision?: "EXACT" | "APPROXIMATE" | "INFERRED";
  match_confidence?: number;
  needs_review?: boolean;
  created_at: string;
  applied_date?: string;
  last_updated_at: string;
  last_email_received_at?: string;
}

export interface ApplicationEvent {
  id: string;
  application_id: string;
  event_type: ApplicationEventType;
  event_date: string;
  description?: string;
  email_id?: string;
  gmail_url?: string;
  email_received_at?: string;
  source_type?: "EMAIL" | "LINKEDIN_EASY_APPLY" | "MANUAL";
  source_id?: string;
  is_inferred?: boolean;
  confidence_score?: number;
  created_at: string;
}

export interface ApplicationEventWithJobInfo extends ApplicationEvent {
  company: string;
  role: string;
  application_status: ApplicationStatus;
  location?: string;
  application_user_id: string;
}

export interface Email {
  id: string;
  application_id?: string;
  user_id: string;
  email_id: string;
  subject: string;
  sender: string;
  body_text: string;
  body_html?: string;
  received_date: string;
  parsed: boolean;
  parsing_confidence?: number;
  created_at: string;
}

export interface EmailRef {
  id: string;
  user_id: string;
  application_id?: string;
  email_id: string;
  external_email_id: string;
  thread_id?: string;
  history_id?: number;
  received_at: string;
  created_at: string;
  gmail_url?: string;
}

export interface StatusCounts {
  APPLIED: number;
  ASSESSMENT: number;
  INTERVIEW: number;
  REJECTED: number;
  OFFERED: number;
  ACCEPTED: number;
  WITHDRAWN: number;
}

export interface TimelineEvent {
  id: string;
  application_id: string;
  event_type: ApplicationEventType;
  event_date: string;
  description?: string;
  email_id?: string;
  company?: string;
  role?: string;
  source_type?: "EMAIL" | "LINKEDIN_EASY_APPLY" | "MANUAL";
  confidence_score?: number;
  is_inferred?: boolean;
}

export interface ApplicationSource {
  source_id: string;
  user_id: string;
  source_type: "EMAIL" | "LINKEDIN_EASY_APPLY";
  external_source_id?: string;
  application_id?: string;
  company_raw: string;
  role_raw: string;
  applied_at_raw?: string;
  observed_at?: string;
  sender_domain?: string;
  source_url?: string;
  payload_json?: Record<string, unknown>;
  merge_confidence?: number;
  merge_status?:
    | "AUTO_MERGED"
    | "PENDING_REVIEW"
    | "UNMATCHED"
    | "MANUALLY_CONFIRMED"
    | "MANUALLY_SEPARATED";
  review_reason?: string;
  created_at?: string;
}

export interface ReviewQueueItem {
  source_id: string;
  source_type: "EMAIL" | "LINKEDIN_EASY_APPLY";
  company: string;
  role: string;
  sender_domain?: string;
  candidate_application_id?: string;
  candidate_company?: string;
  candidate_role?: string;
  confidence_score: number;
  review_reason: string;
  observed_at?: string;
  applied_at?: string;
  status_text?: string;
  source_url?: string;
}

export interface ReviewQueueResponse {
  items: ReviewQueueItem[];
  pending_count: number;
}

export interface SankeyNode {
  id: string;
  label: string;
  count: number;
  stage?: string;
  kind?: string;
  column?: number;
}

export interface SankeyLink {
  source: string;
  target: string;
  value: number;
  kind?: string;
  application_ids?: string[];
  label?: string;
}

export interface SankeyMeta {
  total_applications: number;
  inferred_count?: number;
  pending_review_count?: number;
  ghosted_count?: number;
  start_date?: string;
  end_date?: string;
}

export interface SankeyResponse {
  nodes: SankeyNode[];
  links: SankeyLink[];
  meta?: SankeyMeta;
}

export interface SankeySnapshotFilters {
  preset: "all" | "last30" | "last90" | "custom";
  start_date?: string;
  end_date?: string;
}

export interface SankeySnapshotCache {
  generated_at: string;
  schema_version: number;
  filters: SankeySnapshotFilters;
  payload: SankeyResponse;
}

export interface LinkedInImportSummary {
  processed_rows: number;
  created_applications: number;
  merged_applications: number;
  review_items: number;
  failed_rows: number;
  message?: string;
}

export interface LinkedInImportResult {
  summary: LinkedInImportSummary;
  errors?: Array<{
    row_number: number;
    message: string;
  }>;
}

export interface FinalRoundToggleResponse {
  application_id: string;
  is_final_round: boolean;
  event_id?: string;
}

// Email parsing types for backend API
export interface EmailParseRequest {
  email_id: string;
  subject: string;
  body_text: string;
  body_html?: string;
  received_date: string;
  sender: string;
}

export interface EmailParseResponse {
  company: string;
  role: string;
  status: ApplicationStatus;
  job_posting_url?: string;
  location?: string;
  salary_range?: string;
  notes?: string;
  confidence_score: number;
}

export interface UserPreferences {
  user_id: string;
  gmail_email: string;
}
