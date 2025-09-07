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
  | "APPLICATION_VIEWED"
  | "APPLICATION_REVIEWED"
  | "ASSESSMENT_RECEIVED"
  | "ASSESSMENT_COMPLETED"
  | "INTERVIEW_SCHEDULED"
  | "INTERVIEW_COMPLETED"
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
  created_at: string;
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
