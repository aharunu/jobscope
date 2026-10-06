import React from 'react';
import { fireEvent, render, screen, waitFor, cleanup } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import DedupPage from '@/app/dedup/page';

const api = vi.hoisted(() => ({ list: vi.fn(), merge: vi.fn(), keepSeparate: vi.fn() }));
vi.mock('@/lib/api/dedup', () => ({ dedupApi: api }));
const item = { id: 'candidate', outcome: 'REVIEW', score: 70, signals: { company_exact: true, reference_equal: false }, jobs: ['A', 'B'].map(id => ({ id, company: 'Example', title: 'Engineer', location: 'Istanbul', description: `Description ${id}`, employment_type: 'Full-time', work_mode: 'Hybrid', published_at: null, sources: [{ source: `Board ${id}`, ats_type: 'hirex', status: 'ACTIVE' }] })) };
beforeEach(() => {
  vi.resetAllMocks();
  api.list.mockResolvedValue({ items: [item], total: 1 });
  api.merge.mockResolvedValue({ ...item, resolution: 'MERGED' });
  api.keepSeparate.mockResolvedValue({ ...item, resolution: 'KEEP_SEPARATE' });
});
afterEach(cleanup);

it('renders both vacancies and signals, and requires explicit merge confirmation', async () => {
  render(<DedupPage />);
  await screen.findByText('Description A');
  expect(screen.getByText('Description B')).toBeInTheDocument();
  expect(screen.getByText('reference equal')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Merge' }));
  expect(api.merge).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(api.merge).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Merge' }));
  api.list.mockResolvedValue({ items: [], total: 0 });
  fireEvent.click(screen.getByRole('button', { name: 'Confirm merge' }));
  await screen.findByText(/Jobs merged/);
  expect(api.merge).toHaveBeenCalledWith('candidate');
  await screen.findByText('No pending candidates.');
});

it('keeps jobs separate and refreshes the authoritative pending queue', async () => {
  render(<DedupPage />);
  await screen.findByText('Description A');
  api.list.mockResolvedValue({ items: [], total: 0 });
  fireEvent.click(screen.getByRole('button', { name: 'Keep Separate' }));
  await screen.findByText('Jobs kept separate.');
  expect(api.keepSeparate).toHaveBeenCalledWith('candidate');
  await waitFor(() => expect(api.list).toHaveBeenCalledTimes(2));
});

it('retains review and confirmation on merge failure', async () => {
  api.merge.mockRejectedValue(new Error('DEDUP_APPLICATION_CONFLICT'));
  render(<DedupPage />);
  fireEvent.click(await screen.findByRole('button', { name: 'Merge' }));
  fireEvent.click(screen.getByRole('button', { name: 'Confirm merge' }));
  await screen.findByText('DEDUP_APPLICATION_CONFLICT');
  expect(screen.getByText('Description A')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Confirm merge' })).toBeEnabled();
});

it('prevents duplicate merge submissions', async () => {
  api.merge.mockReturnValue(new Promise(() => {}));
  render(<DedupPage />);
  fireEvent.click(await screen.findByRole('button', { name: 'Merge' }));
  const confirm = screen.getByRole('button', { name: 'Confirm merge' });
  fireEvent.click(confirm); fireEvent.click(confirm);
  expect(api.merge).toHaveBeenCalledTimes(1);
  expect(confirm).toBeDisabled();
});
