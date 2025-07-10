
import { JobApplication, TimelineEvent } from '../types/application';

export const mockApplications: JobApplication[] = [
  {
    id: '1',
    company: 'TechCorp Inc.',
    position: 'Senior Frontend Developer',
    status: 'in-progress',
    dateApplied: '2024-01-15',
    lastUpdate: '2024-01-22',
    location: 'San Francisco, CA',
    salary: '$120,000 - $150,000',
    source: 'LinkedIn',
    notes: 'Had initial phone screening, waiting for technical interview',
    contactPerson: 'Sarah Johnson',
    email: 'sarah.johnson@techcorp.com'
  },
  {
    id: '2',
    company: 'StartupXYZ',
    position: 'Full Stack Engineer',
    status: 'applied',
    dateApplied: '2024-01-20',
    lastUpdate: '2024-01-20',
    location: 'Remote',
    salary: '$90,000 - $120,000',
    source: 'Company Website',
    notes: 'Application submitted through their careers page'
  },
  {
    id: '3',
    company: 'BigTech Solutions',
    position: 'React Developer',
    status: 'offer',
    dateApplied: '2024-01-10',
    lastUpdate: '2024-01-25',
    location: 'New York, NY',
    salary: '$130,000 - $160,000',
    source: 'Recruiter',
    notes: 'Offer received! Need to respond by end of week',
    contactPerson: 'Mike Chen',
    email: 'mike.chen@bigtechsolutions.com'
  },
  {
    id: '4',
    company: 'InnovateLabs',
    position: 'Frontend Architect',
    status: 'rejected',
    dateApplied: '2024-01-05',
    lastUpdate: '2024-01-18',
    location: 'Austin, TX',
    salary: '$140,000 - $170,000',
    source: 'Indeed',
    notes: 'Went through 3 rounds, ultimately went with another candidate'
  },
  {
    id: '5',
    company: 'CloudFirst',
    position: 'UI/UX Developer',
    status: 'in-progress',
    dateApplied: '2024-01-12',
    lastUpdate: '2024-01-24',
    location: 'Seattle, WA',
    salary: '$100,000 - $130,000',
    source: 'AngelList',
    notes: 'Completed take-home assignment, scheduled for final interview',
    contactPerson: 'Lisa Wong'
  },
  {
    id: '6',
    company: 'DataDriven Co',
    position: 'Frontend Engineer',
    status: 'applied',
    dateApplied: '2024-01-25',
    lastUpdate: '2024-01-25',
    location: 'Chicago, IL',
    salary: '$95,000 - $125,000',
    source: 'Glassdoor'
  }
];

export const mockTimelineEvents: TimelineEvent[] = [
  {
    id: '1',
    applicationId: '3',
    company: 'BigTech Solutions',
    position: 'React Developer',
    status: 'offer',
    date: '2024-01-25',
    description: 'Received job offer'
  },
  {
    id: '2',
    applicationId: '5',
    company: 'CloudFirst',
    position: 'UI/UX Developer',
    status: 'in-progress',
    date: '2024-01-24',
    description: 'Scheduled final interview'
  },
  {
    id: '3',
    applicationId: '1',
    company: 'TechCorp Inc.',
    position: 'Senior Frontend Developer',
    status: 'in-progress',
    date: '2024-01-22',
    description: 'Completed phone screening'
  },
  {
    id: '4',
    applicationId: '2',
    company: 'StartupXYZ',
    position: 'Full Stack Engineer',
    status: 'applied',
    date: '2024-01-20',
    description: 'Application submitted'
  },
  {
    id: '5',
    applicationId: '4',
    company: 'InnovateLabs',
    position: 'Frontend Architect',
    status: 'rejected',
    date: '2024-01-18',
    description: 'Application rejected after final interview'
  }
];
