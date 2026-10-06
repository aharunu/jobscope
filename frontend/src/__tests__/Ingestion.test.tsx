import React from 'react';
import { act, fireEvent, render, screen, waitFor, within, cleanup } from '@testing-library/react';
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import IngestionPage from '@/app/ingestion/page';

const api = vi.hoisted(() => ({ catalog: vi.fn(), runs: vi.fn(), defaultPolicy: vi.fn(), sourcePolicy: vi.fn(), saveDefault: vi.fn(), saveSource: vi.fn(), deleteSource: vi.fn(), start: vi.fn(), run: vi.fn(), sources: vi.fn(), decisions: vi.fn(), cancel: vi.fn() }));
vi.mock('@/lib/api/ingestion', () => ({ ingestionApi: api }));
const counts = { jobs_discovered: 5, jobs_accepted: 2, jobs_rejected: 3, jobs_created: 0, jobs_updated: 0, jobs_unchanged: 0, jobs_closed: 0 };
const run = { ...counts, id: 'run1', mode: 'PREVIEW', status: 'COMPLETED', created_at: '2026-10-05T12:00:00Z', cancel_requested_at: null, sources_total: 1, sources_completed: 1, progress: { ...counts, percentage: 100, sources_total: 1, sources_completed: 1, sources_succeeded: 1, sources_partial: 0, sources_failed: 0, current_source_name: null } };
const policy = { allowed_country_codes: ['TR'], enabled: true, include_unknown_country: false };
const units = ['COMPLETED', 'PARTIAL', 'FAILED'].map((status, i) => ({ ...counts, id: `unit${i}`, source_id: 'source1', source_name: `Board ${i}`, ats_type: 'lever', status, duration_ms: 1000, acquisition_complete: i === 0, closure_authorized: false, closure_suppression_reason: 'INGESTION_POLICY_FILTER_ACTIVE', warnings: i === 1 ? ['coverage_not_proven'] : [], warning_count: i === 1 ? 1 : 0, error_type: i === 2 ? 'NETWORK_ERROR' : null, error_message: i === 2 ? 'Safe error' : null, policy_snapshot: { ...policy, origin: 'RUN_OVERRIDE' } }));

beforeEach(() => {
  vi.resetAllMocks();
  api.catalog.mockResolvedValue([{ id: 'source1', name: 'Board', ats_type: 'lever', active: true }]);
  api.runs.mockResolvedValue({ items: [], total: 0 });
  api.defaultPolicy.mockResolvedValue(null);
  api.sourcePolicy.mockResolvedValue(null);
  api.start.mockResolvedValue(run);
  api.run.mockResolvedValue(run);
  api.sources.mockResolvedValue({ items: units });
  api.decisions.mockResolvedValue({ items: [{ id: 'd1', title: 'Engineer', canonical_url: 'https://jobs.example.com/1', location: 'Germany', resolved_country: 'DE', decision: 'REJECTED', reason: 'COUNTRY_NOT_ALLOWED', source_id: 'source1' }], total: 30 });
  api.saveDefault.mockResolvedValue(policy);
  api.saveSource.mockResolvedValue(policy);
  api.deleteSource.mockResolvedValue({});
});
afterEach(() => { cleanup(); vi.useRealTimers(); });

async function ready() {
  render(<IngestionPage />);
  await screen.findByText(/No global default saved/);
}

describe('Ingestion control center', () => {
  it('persists a completed preview from history using its ID, not the edited form', async () => {
    api.runs.mockResolvedValue({ items: [run], total: 1 });
    await ready();
    const button = await screen.findByRole('button', { name: 'Persist this preview' });
    expect(screen.getByText(/same sources will be fetched again/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Scope'), { target: { value: 'ats' } });
    api.start.mockResolvedValue({ ...run, id: 'persist1', mode: 'PERSIST' });
    fireEvent.click(button);
    await waitFor(() => expect(api.start).toHaveBeenCalledWith({ mode: 'PERSIST', from_preview_run_id: 'run1' }));
  });

  it('keeps the preview visible on persist failure and permits retry', async () => {
    api.runs.mockResolvedValue({ items: [run], total: 1 });
    api.start.mockRejectedValue(new Error('INGESTION_RUN_BUSY'));
    await ready();
    fireEvent.click(await screen.findByRole('button', { name: 'Persist this preview' }));
    await screen.findByText('INGESTION_RUN_BUSY');
    expect(screen.getByRole('button', { name: 'Persist this preview' })).toBeEnabled();
  });

  it('prevents duplicate preview persistence submissions', async () => {
    api.runs.mockResolvedValue({ items: [run], total: 1 });
    api.start.mockReturnValue(new Promise(() => {}));
    await ready();
    const button = await screen.findByRole('button', { name: 'Persist this preview' });
    fireEvent.click(button); fireEvent.click(button);
    expect(api.start).toHaveBeenCalledTimes(1);
    expect(button).toBeDisabled();
  });

  it.each(['FAILED', 'CANCELLED', 'RUNNING'])('does not offer persistence for %s preview', async status => {
    api.runs.mockResolvedValue({ items: [{ ...run, status }], total: 1 });
    api.run.mockResolvedValue({ ...run, status });
    await ready();
    await screen.findByText((_, el) => el?.tagName === 'STRONG' && el.textContent === `PREVIEW · ${status}`);
    expect(screen.queryByRole('button', { name: 'Persist this preview' })).not.toBeInTheDocument();
  });
  it('suggests Turkey without automatically starting or saving', async () => {
    await ready();
    const editor = within(screen.getByRole('region', { name: 'Policy editor' }));
    expect(editor.getByLabelText('Allowed countries')).toHaveValue(['TR']);
    expect(api.start).not.toHaveBeenCalled();
    expect(api.saveDefault).not.toHaveBeenCalled();
  });

  it.each(['PREVIEW', 'PERSIST'])('starts %s with a run override', async mode => {
    await ready();
    fireEvent.change(screen.getByLabelText('Mode'), { target: { value: mode } });
    fireEvent.click(screen.getByRole('button', { name: mode === 'PREVIEW' ? 'Start preview' : 'Start persist' }));
    await waitFor(() => expect(api.start).toHaveBeenCalledWith({ mode, policy_mode: 'OVERRIDE_SELECTED_SOURCES', active_sources_only: true, allowed_country_codes: ['TR'], include_unknown_country: false }));
    await screen.findByText((_, el) => el?.tagName === 'STRONG' && el.textContent === 'PREVIEW · COMPLETED');
  });

  it('uses saved policy mode without sending draft overrides', async () => {
    await ready();
    fireEvent.change(screen.getByLabelText('Policy mode'), { target: { value: 'USE_SAVED_POLICIES' } });
    fireEvent.click(screen.getByRole('button', { name: 'Start preview' }));
    await waitFor(() => expect(api.start).toHaveBeenCalledWith({ mode: 'PREVIEW', policy_mode: 'USE_SAVED_POLICIES', active_sources_only: true }));
  });

  it('selects a source or ATS and prevents empty scope submissions', async () => {
    await ready();
    fireEvent.change(screen.getByLabelText('Scope'), { target: { value: 'sources' } });
    expect(screen.getByRole('button', { name: 'Start preview' })).toBeDisabled();
    const select = screen.getByLabelText('Selected sources') as HTMLSelectElement;
    select.options[0].selected = true; fireEvent.change(select);
    fireEvent.click(screen.getByRole('button', { name: 'Start preview' }));
    await waitFor(() => expect(api.start.mock.calls[0][0].source_ids).toEqual(['source1']));
  });

  it('saves authoritative global policy and source override, then removes override', async () => {
    await ready();
    fireEvent.click(screen.getByRole('button', { name: 'Save policy' }));
    await screen.findByText('Policy saved');
    expect(api.saveDefault).toHaveBeenCalledWith(policy);
    fireEvent.change(screen.getByLabelText('Policy target'), { target: { value: 'source1' } });
    await screen.findByText('No override: inherits global default');
    fireEvent.click(screen.getByRole('button', { name: 'Save policy' }));
    await waitFor(() => expect(api.saveSource).toHaveBeenCalledWith('source1', policy));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Remove override' })).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: 'Remove override' }));
    await screen.findByText(/Override removed/);
    expect(api.deleteSource).toHaveBeenCalledWith('source1');
  });

  it('renders counts, status distinctions, closure and compact decisions with filters/paging', async () => {
    api.runs.mockResolvedValue({ items: [run], total: 1 });
    await ready();
    await screen.findByText((_, el) => el?.tagName === 'STRONG' && el.textContent === 'PREVIEW · COMPLETED');
    expect(screen.getByText((_, el) => el?.tagName === 'SUMMARY' && !!el.textContent?.includes('Board 1 · lever · PARTIAL'))).toBeInTheDocument();
    expect(screen.getByText((_, el) => el?.tagName === 'SUMMARY' && !!el.textContent?.includes('Board 2 · lever · FAILED'))).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('value', '100');
    expect(screen.getByText('Engineer')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Decision filter'), { target: { value: 'REJECTED' } });
    await waitFor(() => expect(api.decisions).toHaveBeenLastCalledWith('run1', expect.objectContaining({ decision: 'REJECTED', offset: 0 })));
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    await waitFor(() => expect(api.decisions).toHaveBeenLastCalledWith('run1', expect.objectContaining({ decision: 'REJECTED', offset: 25 })));
  });

  it('keeps draft and shows safe errors on failure without success notice', async () => {
    api.start.mockRejectedValue(new Error('INGESTION_RUN_BUSY: Another run is active'));
    await ready();
    fireEvent.click(screen.getByRole('button', { name: 'Start preview' }));
    await screen.findByText(/INGESTION_RUN_BUSY/);
    expect(within(screen.getByRole('region', { name: 'Run configuration' })).getByLabelText('Allowed countries')).toHaveValue(['TR']);
    expect(screen.getByRole('button', { name: 'Start preview' })).toBeEnabled();
  });

  it('prevents duplicate submissions while waiting for the response', async () => {
    api.start.mockReturnValue(new Promise(() => {}));
    await ready();
    fireEvent.click(screen.getByRole('button', { name: 'Start preview' }));
    expect(screen.getAllByRole('button', { name: 'Loading...' })[0]).toBeDisabled();
    expect(api.start).toHaveBeenCalledTimes(1);
  });

  it('polls running progress, requests cooperative cancellation and stops on terminal status', async () => {
    const running = { ...run, status: 'RUNNING', sources_completed: 0, progress: { ...run.progress, percentage: 0, current_source_name: 'Board' } };
    api.runs.mockResolvedValue({ items: [running], total: 1 });
    api.run.mockResolvedValueOnce(running).mockResolvedValue({ ...run, status: 'CANCELLED' });
    api.cancel.mockResolvedValue({ ...running, cancel_requested_at: 'now' });
    await ready();
    await screen.findByRole('button', { name: 'Cancel after current source' });
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel after current source' }));
    await act(async () => { await Promise.resolve(); });
    expect(api.cancel).toHaveBeenCalledWith('run1');
    await act(async () => { await vi.advanceTimersByTimeAsync(1500); });
    // The initial timer was registered before fake timers: explicitly remount
    // with fake timers to prove polling shutdown deterministically.
    cleanup(); api.run.mockClear(); api.run.mockResolvedValueOnce(running).mockResolvedValue({ ...run, status: 'CANCELLED' });
    render(<IngestionPage />);
    await act(async () => { await vi.advanceTimersByTimeAsync(0); });
    await act(async () => { await vi.advanceTimersByTimeAsync(1500); });
    expect(screen.getByText((_, el) => el?.tagName === 'STRONG' && el.textContent === 'PREVIEW · CANCELLED')).toBeInTheDocument();
    const calls = api.run.mock.calls.length;
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    expect(api.run).toHaveBeenCalledTimes(calls);
  });
});
