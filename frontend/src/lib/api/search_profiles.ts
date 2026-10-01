/**
 * Search Profiles API functions.
 */

import { apiClient } from './client';
import { SearchProfileCreateRequest, SearchProfileResponse } from './types';

export async function listSearchProfiles(
  signal?: AbortSignal,
): Promise<SearchProfileResponse[]> {
  return apiClient<SearchProfileResponse[]>('/api/search-profiles', {
    method: 'GET',
    signal,
  });
}

export async function createSearchProfile(
  payload: SearchProfileCreateRequest,
  signal?: AbortSignal,
): Promise<SearchProfileResponse> {
  return apiClient<SearchProfileResponse>('/api/search-profiles', {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  });
}

export async function deleteSearchProfile(
  id: string,
  signal?: AbortSignal,
): Promise<void> {
  await apiClient<void>(`/api/search-profiles/${id}`, {
    method: 'DELETE',
    signal,
  });
}
