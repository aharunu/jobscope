import { apiClient } from './client';

export type ReviewJob = { id: string; company: string; title: string; location: string | null; employment_type: string | null; work_mode: string | null; published_at: string | null; description: string; merged_into_id: string | null; sources: { source: string; ats_type: string; url: string; status: string }[] };
export type DedupCandidate = { id: string; score: number; outcome: string; signals: Record<string, boolean | number | string | null>; resolved_at: string | null; resolution: string | null; jobs: ReviewJob[] };
export const dedupApi = {
  list: (offset = 0) => apiClient<{ items: DedupCandidate[]; total: number }>('/api/dedup/candidates', { params: { limit: 25, offset } }),
  detail: (id: string) => apiClient<DedupCandidate>(`/api/dedup/candidates/${id}`),
  merge: (id: string) => apiClient<DedupCandidate>(`/api/dedup/candidates/${id}/merge`, { method: 'POST', body: JSON.stringify({ confirm: true }) }),
  keepSeparate: (id: string) => apiClient<DedupCandidate>(`/api/dedup/candidates/${id}/keep-separate`, { method: 'POST' }),
};
