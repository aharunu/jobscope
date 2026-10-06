import { expect, it, vi } from 'vitest';
import { listSourcePlatforms } from '../lib/api/sources';

const client = vi.hoisted(() => vi.fn());
vi.mock('../lib/api/client', () => ({ apiClient: client }));

it('loads all registry pages without restricting to active sources and deduplicates platforms', async () => {
  client.mockResolvedValueOnce({ items: [{ ats_type: 'hirex' }], total: 3 })
    .mockResolvedValueOnce({ items: [{ ats_type: 'ashby' }, { ats_type: 'hirex' }], total: 3 });
  const signal = new AbortController().signal;
  expect(await listSourcePlatforms(signal)).toEqual(['ashby', 'hirex']);
  expect(client.mock.calls).toEqual([
    ['/api/sources', { params: { limit: 1000, offset: 0 }, signal }],
    ['/api/sources', { params: { limit: 1000, offset: 1 }, signal }],
  ]);
});
