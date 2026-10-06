import { beforeEach, expect, it, vi } from 'vitest';
import { ingestionApi } from '@/lib/api/ingestion';
const client = vi.hoisted(() => vi.fn());
vi.mock('@/lib/api/client', () => ({ apiClient: client }));
beforeEach(() => client.mockReset());

it('uses the existing /api rewrite for every ingestion endpoint', async () => {
  client.mockResolvedValue({});
  const policy = { allowed_country_codes: ['TR'], include_unknown_country: false, enabled: true };
  await ingestionApi.defaultPolicy();
  await ingestionApi.saveDefault(policy);
  await ingestionApi.sourcePolicy('source');
  await ingestionApi.saveSource('source', policy);
  await ingestionApi.deleteSource('source');
  await ingestionApi.start({ mode: 'PREVIEW', policy_mode: 'USE_SAVED_POLICIES', active_sources_only: true });
  await ingestionApi.runs();
  await ingestionApi.run('run');
  await ingestionApi.sources('run');
  await ingestionApi.decisions('run', { limit: 25, offset: 0 });
  await ingestionApi.cancel('run');
  expect(client.mock.calls.map(call => call[0])).toEqual([
    '/api/ingestion/policies/default', '/api/ingestion/policies/default',
    '/api/ingestion/policies/sources/source', '/api/ingestion/policies/sources/source', '/api/ingestion/policies/sources/source',
    '/api/ingestion/runs', '/api/ingestion/runs', '/api/ingestion/runs/run',
    '/api/ingestion/runs/run/sources', '/api/ingestion/runs/run/decisions', '/api/ingestion/runs/run/cancel',
  ]);
  expect(client.mock.calls[5][1]).toMatchObject({ method: 'POST', body: JSON.stringify({ mode: 'PREVIEW', policy_mode: 'USE_SAVED_POLICIES', active_sources_only: true }) });
});

it('loads existing registry sources using the /api prefix and all catalog pages', async () => {
  client.mockResolvedValueOnce({ items: [{ id: 'one' }], total: 2 }).mockResolvedValueOnce({ items: [{ id: 'two' }], total: 2 });
  expect(await ingestionApi.catalog()).toEqual([{ id: 'one' }, { id: 'two' }]);
  expect(client.mock.calls).toEqual([
    ['/api/sources', { params: { limit: 1000, offset: 0 } }],
    ['/api/sources', { params: { limit: 1000, offset: 1 } }],
  ]);
});
