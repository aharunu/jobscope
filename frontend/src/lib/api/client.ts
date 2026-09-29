/**
 * Core API Client for JobScope Frontend.
 *
 * Communicates with backend endpoints via same-origin Next.js rewrites (/api/...).
 * Handles query string serialization, optional AbortSignal, and normalized error throwing.
 */

import { ApiError, ApiErrorDetail } from './types';

const API_BASE = ''; // Uses same-origin Next.js rewrites to /api/...

export interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined | null>;
  signal?: AbortSignal;
}

export function buildQueryString(
  params?: Record<string, string | number | boolean | undefined | null>,
): string {
  if (!params) return '';

  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  }

  const query = searchParams.toString();
  return query ? `?${query}` : '';
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<T> {
  const { params, headers, signal, ...restOptions } = options;
  const queryString = buildQueryString(params);
  const url = `${API_BASE}${endpoint}${queryString}`;

  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(headers as Record<string, string>),
  };

  // Only include X-User-Id if explicitly configured in environment
  const configuredUserId = process.env.NEXT_PUBLIC_USER_ID;
  if (configuredUserId && configuredUserId.trim()) {
    requestHeaders['X-User-Id'] = configuredUserId.trim();
  }

  try {
    const response = await fetch(url, {
      ...restOptions,
      headers: requestHeaders,
      signal,
    });

    if (!response.ok) {
      let errorDetail: string | ApiErrorDetail[] = `Request failed with status ${response.status}`;
      try {
        const errorData = (await response.json()) as { detail?: string | ApiErrorDetail[] };
        if (errorData && errorData.detail) {
          errorDetail = errorData.detail;
        }
      } catch {
        // Response was not JSON
      }
      throw new ApiError(response.status, errorDetail);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return (await response.json()) as T;
  } catch (err: unknown) {
    if (err instanceof ApiError) {
      throw err;
    }
    if ((err instanceof DOMException || err instanceof Error) && err.name === 'AbortError') {
      throw err; // Let caller recognize intentional cancellation
    }
    throw new ApiError(500, err instanceof Error ? err.message : 'Network error');
  }
}
