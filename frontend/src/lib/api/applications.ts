import { apiClient } from './client';
import type { Application, ApplicationHistory, ApplicationListResponse, ApplicationStatus } from './types';

export const listApplications = (params: {status?: ApplicationStatus; job_id?: string; limit?: number; offset?: number} = {}, signal?: AbortSignal) =>
  apiClient<ApplicationListResponse>('/api/applications', {params, signal, cache: 'no-store'});
export const createApplication = (jobId: string, signal?: AbortSignal) =>
  apiClient<Application>('/api/applications', {method: 'POST', body: JSON.stringify({job_id: jobId, status: 'INTERESTED'}), signal});
const path = (id: string) => `/api/applications/${encodeURIComponent(id)}`;
export const getApplication = (id: string, signal?: AbortSignal) =>
  apiClient<Application>(path(id), {signal, cache: 'no-store'});
export const updateApplicationStatus = (id: string, status: ApplicationStatus, signal?: AbortSignal) =>
  apiClient<Application>(`${path(id)}/status`, {method: 'PATCH', body: JSON.stringify({status}), signal});
export const updateApplicationNotes = (id: string, notes: string | null, signal?: AbortSignal) =>
  apiClient<Application>(`${path(id)}/notes`, {method: 'PATCH', body: JSON.stringify({notes}), signal});
export const getApplicationHistory = (id: string, signal?: AbortSignal) =>
  apiClient<ApplicationHistory[]>(`${path(id)}/history`, {signal, cache: 'no-store'});
export const deleteApplication = (id: string, signal?: AbortSignal) =>
  apiClient<void>(path(id), {method: 'DELETE', signal});
