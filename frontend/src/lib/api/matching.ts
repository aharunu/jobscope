/**
 * Deterministic Matching API functions.
 */

import { apiClient } from './client';
import { MatchRequest, MatchResultResponse } from './types';

export const analyzeMatch = (id: string, force = false, signal?: AbortSignal) =>
  apiClient<MatchResultResponse>(`/api/matches/${encodeURIComponent(id)}/ai`, {method: 'POST', params: {force}, signal});

export async function evaluateMatch(
  payload: MatchRequest,
  signal?: AbortSignal,
): Promise<MatchResultResponse> {
  return apiClient<MatchResultResponse>('/api/matches', {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  });
}

export async function getSavedMatch(jobId: string, searchProfileId: string, signal?: AbortSignal): Promise<MatchResultResponse> {
  return apiClient<MatchResultResponse>(`/api/matches/job/${encodeURIComponent(jobId)}`, {
    params: {search_profile_id: searchProfileId}, signal, cache: 'no-store',
  });
}
