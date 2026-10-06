import { apiClient } from './client';

/** Read all registry platforms, including inactive sources with historical jobs. */
export async function listSourcePlatforms(signal?: AbortSignal): Promise<string[]> {
  const platforms = new Set<string>();
  let offset = 0;
  while (true) {
    const page = await apiClient<{ items: { ats_type: string }[]; total: number }>(
      '/api/sources', { params: { limit: 1000, offset }, signal },
    );
    for (const source of page.items) platforms.add(source.ats_type);
    offset += page.items.length;
    if (offset >= page.total || !page.items.length) return [...platforms].sort();
  }
}
