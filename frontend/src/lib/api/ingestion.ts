import { apiClient } from './client';

export type Policy = { allowed_country_codes: string[]; include_unknown_country: boolean; enabled: boolean };
export type Mode = 'PREVIEW' | 'PERSIST';
export type PolicyMode = 'USE_SAVED_POLICIES' | 'OVERRIDE_SELECTED_SOURCES';
export type StartRequest = { mode: Mode; policy_mode: PolicyMode; source_ids?: string[]; ats_types?: string[]; active_sources_only: boolean; allowed_country_codes?: string[]; include_unknown_country?: boolean } | { mode: 'PERSIST'; from_preview_run_id: string };
export type Source = { id: string; name: string; ats_type: string; active: boolean };
export type Counts = { jobs_discovered: number; jobs_accepted: number; jobs_rejected: number; jobs_created: number; jobs_updated: number; jobs_unchanged: number; jobs_closed: number };
export type Run = Counts & { id: string; mode: Mode; status: string; created_at: string; cancel_requested_at: string | null; sources_total: number; sources_completed: number; progress?: Counts & { percentage: number; sources_total: number; sources_completed: number; sources_succeeded: number; sources_partial: number; sources_failed: number; current_source_name: string | null } };
export type SourceRun = Counts & { id: string; source_id: string; source_name: string; ats_type: string; status: string; duration_ms: number; acquisition_complete: boolean; closure_authorized: boolean; closure_suppression_reason: string | null; warnings: string[]; warning_count: number; error_type: string | null; error_message: string | null; policy_snapshot: Policy & { origin: string } };
export type Decision = { id: string; title: string | null; canonical_url: string; location: string | null; resolved_country: string | null; decision: string; reason: string; source_id: string; external_job_id: string | null };
export type DecisionFilters = { decision?: string; source_id?: string; reason?: string; country?: string; offset: number; limit: number };

export const ingestionApi = {
  defaultPolicy: () => apiClient<Policy | null>('/api/ingestion/policies/default'),
  saveDefault: (policy: Policy) => apiClient<Policy>('/api/ingestion/policies/default', { method: 'PUT', body: JSON.stringify(policy) }),
  sourcePolicy: (id: string) => apiClient<Policy | null>(`/api/ingestion/policies/sources/${id}`),
  saveSource: (id: string, policy: Policy) => apiClient<Policy>(`/api/ingestion/policies/sources/${id}`, { method: 'PUT', body: JSON.stringify(policy) }),
  deleteSource: (id: string) => apiClient(`/api/ingestion/policies/sources/${id}`, { method: 'DELETE' }),
  start: (request: StartRequest) => apiClient<Run>('/api/ingestion/runs', { method: 'POST', body: JSON.stringify(request) }),
  runs: () => apiClient<{ items: Run[]; total: number }>('/api/ingestion/runs'),
  run: (id: string) => apiClient<Run>(`/api/ingestion/runs/${id}`),
  sources: (id: string) => apiClient<{ items: SourceRun[] }>(`/api/ingestion/runs/${id}/sources`),
  decisions: (id: string, params: DecisionFilters) => apiClient<{ items: Decision[]; total: number }>(`/api/ingestion/runs/${id}/decisions`, { params }),
  cancel: (id: string) => apiClient<Run>(`/api/ingestion/runs/${id}/cancel`, { method: 'POST' }),
  catalog: async () => {
    let offset = 0;
    const items: Source[] = [];
    while (true) {
      const page = await apiClient<{ items: Source[]; total: number }>('/api/sources', { params: { limit: 1000, offset } });
      items.push(...page.items);
      offset += page.items.length;
      if (offset >= page.total || !page.items.length) return items;
    }
  },
};
