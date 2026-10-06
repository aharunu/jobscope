import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { renderToString } from 'react-dom/server';
import { hydrateRoot } from 'react-dom/client';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import IngestionPage from '@/app/ingestion/page';

const api = vi.hoisted(() => ({ catalog: vi.fn(), runs: vi.fn(), defaultPolicy: vi.fn(), sourcePolicy: vi.fn(), run: vi.fn(), sources: vi.fn(), decisions: vi.fn(), start: vi.fn(), saveDefault: vi.fn(), saveSource: vi.fn(), deleteSource: vi.fn(), cancel: vi.fn() }));
vi.mock('@/lib/api/ingestion', () => ({ ingestionApi: api }));
const counts = { jobs_discovered: 0, jobs_accepted: 0, jobs_rejected: 0, jobs_created: 0, jobs_updated: 0, jobs_unchanged: 0, jobs_closed: 0 };
const preview = { ...counts, id: 'preview', mode: 'PREVIEW', status: 'COMPLETED', created_at: '2026-10-07T00:00:00Z', sources_total: 1, sources_completed: 1 };
beforeEach(() => {
  vi.resetAllMocks();
  api.catalog.mockResolvedValue([{ id: 'source', name: 'Audit Source', ats_type: 'lever', active: true }]);
  api.runs.mockResolvedValue({ items: [], total: 0 });
  api.defaultPolicy.mockResolvedValue(null);
  api.sourcePolicy.mockResolvedValue({ allowed_country_codes: ['US'], include_unknown_country: true, enabled: true });
  api.sources.mockResolvedValue({ items: [] });
  api.decisions.mockResolvedValue({ items: [], total: 0 });
  api.start.mockRejectedValue(new Error('Audit stopped before start'));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it('hydrates stable country codes even when server and browser ICU names differ', async () => {
  const displayName = vi.spyOn(Intl.DisplayNames.prototype, 'of').mockReturnValue('Server region name');
  const html = renderToString(<IngestionPage />);
  expect(html).not.toContain('Server region name');
  expect(html).toContain('value="FK"');
  const container = document.createElement('div');
  container.innerHTML = html;
  document.body.append(container);
  displayName.mockReturnValue('Browser region name');
  const onRecoverableError = vi.fn();
  let root: ReturnType<typeof hydrateRoot>;
  await act(async () => { root = hydrateRoot(container, <IngestionPage />, { onRecoverableError }); });
  expect(onRecoverableError).not.toHaveBeenCalled();
  expect(within(container).getAllByRole('option', { name: 'Browser region name (FK)' })).toHaveLength(2);
  expect(within(container).getAllByRole('listbox', { name: 'Allowed countries' })[0]).toHaveValue(['TR']);
  await act(async () => { root.unmount(); });
  container.remove();
});

it('saved policy edits and target loading do not alter the run override', async () => {
  render(<IngestionPage />);
  await screen.findByRole('option', { name: 'Audit Source' });
  const run = within(screen.getByRole('region', { name: 'Run configuration' }));
  const editor = within(screen.getByRole('region', { name: 'Policy editor' }));
  fireEvent.change(editor.getByRole('listbox', { name: 'Allowed countries' }), { target: { value: 'ES' } });
  expect(run.getByRole('listbox', { name: 'Allowed countries' })).toHaveValue(['TR']);
  fireEvent.change(editor.getByRole('combobox', { name: 'Policy target' }), { target: { value: 'source' } });
  await screen.findByText('Saved policy exists');
  expect(editor.getByRole('listbox', { name: 'Allowed countries' })).toHaveValue(['US']);
  expect(run.getByRole('listbox', { name: 'Allowed countries' })).toHaveValue(['TR']);
  fireEvent.click(run.getByRole('button', { name: 'Start preview' }));
  await waitFor(() => expect(api.start).toHaveBeenCalledWith(expect.objectContaining({ allowed_country_codes: ['TR'], include_unknown_country: false })));
});

it('history selection does not enable another run or persist while a run is active', async () => {
  const current = { ...preview, id: 'active', status: 'RUNNING', sources_completed: 0 };
  api.runs.mockResolvedValue({ items: [current, preview], total: 2 });
  api.run.mockImplementation(async (id: string) => id === 'active' ? current : preview);
  render(<IngestionPage />);
  await screen.findByRole('option', { name: /PREVIEW · COMPLETED/ });
  fireEvent.change(screen.getByRole('combobox', { name: 'Run history' }), { target: { value: 'preview' } });
  const persist = await screen.findByRole('button', { name: 'Persist this preview' });
  expect(persist).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Start preview' })).toBeDisabled();
  expect(screen.getByText(/A run is active/)).toBeInTheDocument();
});

it('explains policy acceptance vs processing and shows safe source errors and empty decisions', async () => {
  const failed = { ...preview, mode: 'PERSIST', status: 'COMPLETED_WITH_WARNINGS', jobs_discovered: 2, jobs_accepted: 2 };
  api.runs.mockResolvedValue({ items: [failed], total: 1 });
  api.run.mockResolvedValue(failed);
  api.sources.mockResolvedValue({ items: [{ ...counts, id: 'unit', source_id: 'source', source_name: 'Audit Source', ats_type: 'lever', status: 'FAILED', duration_ms: 1, warnings: ['JOB_URL_OWNERSHIP_CONFLICT'], warning_count: 1, error_type: 'INGESTION_ITEM_FAILURE', error_message: '2 accepted postings could not be processed: JOB_URL_OWNERSHIP_CONFLICT', policy_snapshot: { origin: 'RUN_OVERRIDE', allowed_country_codes: ['TR'], enabled: true } }] });
  render(<IngestionPage />);
  await screen.findByText(/2 accepted posting\(s\) were not processed/);
  expect(screen.getByText(/INGESTION_ITEM_FAILURE:/)).toBeInTheDocument();
  expect(screen.getByText('No decisions match the selected filters.')).toBeInTheDocument();
});
