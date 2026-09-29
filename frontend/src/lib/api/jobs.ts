/**
 * Canonical Jobs API functions.
 */

import { apiClient } from './client';
import { JobDetailResponse, JobFilterParams, JobListResponse } from './types';

export async function listJobs(
  params: JobFilterParams = {},
  signal?: AbortSignal,
): Promise<JobListResponse> {
  return apiClient<JobListResponse>('/api/jobs', {
    method: 'GET',
    params: {
      status: params.status,
      source_id: params.source_id,
      ats_type: params.ats_type,
      company: params.company,
      location: params.location,
      work_mode: params.work_mode,
      employment_type: params.employment_type,
      q: params.q,
      limit: params.limit,
      offset: params.offset,
    },
    signal,
  });
}

export async function getJobById(
  jobId: string,
  signal?: AbortSignal,
): Promise<JobDetailResponse> {
  return apiClient<JobDetailResponse>(`/api/jobs/${jobId}`, {
    method: 'GET',
    signal,
  });
}
