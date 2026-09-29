/**
 * Deterministic Matching API functions.
 */

import { apiClient } from './client';
import { MatchRequest, MatchResultResponse } from './types';

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
