import type { ApplicationStatus } from '@/lib/api/types';

export const APPLICATION_STATUSES: ApplicationStatus[] = ['INTERESTED', 'APPLYING', 'APPLIED', 'INTERVIEW', 'OFFER', 'REJECTED'];
// Mirrors the tested domain policy. The API remains authoritative.
export const APPLICATION_TRANSITIONS: Record<ApplicationStatus, ApplicationStatus[]> = {
  INTERESTED: ['APPLYING', 'APPLIED', 'REJECTED'],
  APPLYING: ['INTERESTED', 'APPLIED', 'REJECTED'],
  APPLIED: ['INTERVIEW', 'OFFER', 'REJECTED'],
  INTERVIEW: ['OFFER', 'REJECTED'], OFFER: ['REJECTED'],
  REJECTED: ['INTERESTED', 'APPLYING', 'APPLIED', 'INTERVIEW'],
};
export const statusLabel = (status: ApplicationStatus) => status.charAt(0) + status.slice(1).toLowerCase();
export function ApplicationStatusBadge({status}: {status: ApplicationStatus}) {
  return <span className={`application-status application-status-${status.toLowerCase()}`}>{statusLabel(status)}</span>;
}
export const applicationDate = (value: string | null) => value ? new Date(value).toLocaleString() : 'Not available';
