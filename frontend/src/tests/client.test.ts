import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { buildQueryString, apiClient } from '../lib/api/client';
import { ApiError } from '../lib/api/types';

describe('API Client & Query Serializer', () => {
  describe('buildQueryString', () => {
    it('returns empty string when params are undefined or empty', () => {
      expect(buildQueryString()).toBe('');
      expect(buildQueryString({})).toBe('');
    });

    it('correctly serializes valid key-value pairs', () => {
      const query = buildQueryString({ q: 'python', limit: 50, offset: 0 });
      expect(query).toBe('?q=python&limit=50&offset=0');
    });

    it('omits null, undefined, and empty string values', () => {
      const query = buildQueryString({
        q: 'engineer',
        company: '',
        location: null,
        work_mode: undefined,
        status: 'ACTIVE',
      });
      expect(query).toBe('?q=engineer&status=ACTIVE');
    });
  });

  describe('apiClient', () => {
    const originalFetch = global.fetch;

    beforeEach(() => {
      vi.resetAllMocks();
    });

    afterEach(() => {
      global.fetch = originalFetch;
    });

    it('fetches successfully and returns parsed JSON', async () => {
      const mockData = { total: 1, jobs: [] };
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockData,
      });

      const result = await apiClient<{ total: number; jobs: any[] }>('/api/jobs', {
        params: { limit: 10 },
      });

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/jobs?limit=10',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
      expect(result).toEqual(mockData);
    });

    it('throws ApiError with detail on HTTP error status', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Job not found' }),
      });

      await expect(apiClient('/api/jobs/unknown-id')).rejects.toThrow('Job not found');
    });

    it('does not send X-User-Id header if NEXT_PUBLIC_USER_ID is not configured', async () => {
      delete process.env.NEXT_PUBLIC_USER_ID;

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({}),
      });

      await apiClient('/api/jobs');

      const calledHeaders = (global.fetch as any).mock.calls[0][1].headers;
      expect(calledHeaders['X-User-Id']).toBeUndefined();
    });

    it('attaches X-User-Id header when NEXT_PUBLIC_USER_ID is explicitly configured', async () => {
      process.env.NEXT_PUBLIC_USER_ID = 'test-user-uuid-123';

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({}),
      });

      await apiClient('/api/jobs');

      const calledHeaders = (global.fetch as any).mock.calls[0][1].headers;
      expect(calledHeaders['X-User-Id']).toBe('test-user-uuid-123');

      delete process.env.NEXT_PUBLIC_USER_ID;
    });
  });
});
