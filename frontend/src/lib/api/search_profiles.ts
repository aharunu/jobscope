/**
 * Search Profiles API functions.
 */

import { apiClient } from './client';
import { SearchProfileResponse } from './types';

export async function listSearchProfiles(
  signal?: AbortSignal,
): Promise<SearchProfileResponse[]> {
  return apiClient<SearchProfileResponse[]>('/api/search-profiles', {
    method: 'GET',
    signal,
  });
}
