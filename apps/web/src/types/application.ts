
export interface JobApplication {
  id: string;
  company: string;
  position: string;
  status: 'applied' | 'in-progress' | 'offer' | 'rejected';
  dateApplied: string;
  lastUpdate: string;
  location?: string;
  salary?: string;
  source: string;
  notes?: string;
  contactPerson?: string;
  email?: string;
}

export interface StatusCounts {
  applied: number;
  'in-progress': number;
  offer: number;
  rejected: number;
}

export interface TimelineEvent {
  id: string;
  applicationId: string;
  company: string;
  position: string;
  status: JobApplication['status'];
  date: string;
  description: string;
}
