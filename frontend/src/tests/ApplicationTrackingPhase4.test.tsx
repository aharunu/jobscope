import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApplicationsClient } from '../components/applications/ApplicationsClient';
import { ApplicationDetailClient } from '../components/applications/ApplicationDetailClient';
import { ApplicationTrackingPanel } from '../components/applications/ApplicationTrackingPanel';
import { ApiError, type Application, type ApplicationListResponse } from '../lib/api/types';

const api = vi.hoisted(() => ({listApplications: vi.fn(), getApplication: vi.fn(), createApplication: vi.fn(), updateApplicationStatus: vi.fn(), updateApplicationNotes: vi.fn(), deleteApplication: vi.fn()}));
const router = vi.hoisted(() => ({push: vi.fn(), refresh: vi.fn()}));
vi.mock('../lib/api/applications', () => api);
vi.mock('next/navigation', () => ({useRouter: () => router}));
const application = (id = 'a', status: Application['status'] = 'INTERESTED'): Application => ({
  id, job_id: `job-${id}`, user_id: 'user', status, notes: null, created_at: '2026-10-01T12:00:00Z', updated_at: '2026-10-02T12:00:00Z',
  job: {id: `job-${id}`, title: `Engineer ${id}`, company: 'Acme', status: 'CLOSED', canonical_url: 'https://example.com', location: null, work_mode: null, employment_type: null, salary: null, source_name: null}, status_history: [],
});
const list = (...items: Application[]): ApplicationListResponse => ({items, total: items.length, limit: 20, offset: 0});
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (error: Error) => void; const promise = new Promise<T>((a,b) => {resolve=a; reject=b;}); return {promise, resolve, reject}; }
beforeEach(() => {vi.resetAllMocks(); api.listApplications.mockResolvedValue(list()); api.getApplication.mockResolvedValue(application()); api.createApplication.mockResolvedValue(application());});

it('offers Applied for Interview and renders the backend persisted correction/history', async () => {
  api.getApplication.mockResolvedValue(application('a', 'INTERVIEW'));
  api.updateApplicationStatus.mockResolvedValue({...application('a', 'APPLIED'), status_history:[{
    id:'correction', application_id:'a', from_status:'INTERVIEW', to_status:'APPLIED', changed_at:'2026-10-04T12:00:00Z',
  }]});
  render(<ApplicationDetailClient applicationId="a"/>);
  const select = await screen.findByLabelText('New status');
  expect(screen.getByRole('option', {name:'Applied'})).toHaveValue('APPLIED');
  expect(api.updateApplicationStatus).not.toHaveBeenCalled();
  fireEvent.change(select, {target:{value:'APPLIED'}});
  fireEvent.click(screen.getByRole('button', {name:'Update status'}));
  await screen.findByText('Interview → Applied');
  expect(api.updateApplicationStatus).toHaveBeenCalledTimes(1);
  expect(api.updateApplicationStatus).toHaveBeenCalledWith('a','APPLIED',expect.any(AbortSignal));
  expect(screen.getByText('Applied', {selector:'span'})).toBeInTheDocument();
});

describe('Applications list', () => {
  it('shows loading then useful empty state', async () => {
    const pending = deferred<ApplicationListResponse>(); api.listApplications.mockReturnValue(pending.promise);
    render(<ApplicationsClient />); expect(screen.getByRole('status')).toHaveTextContent('Loading applications');
    await act(async () => pending.resolve(list()));
    expect(screen.getByText('No applications tracked yet.')).toBeInTheDocument();
    expect(screen.getByRole('link', {name: 'Browse jobs'})).toHaveAttribute('href', '/jobs');
  });
  it('renders embedded job, notes, dates, badge and links without job fetches', async () => {
    api.listApplications.mockResolvedValue(list({...application(), notes: 'Prepare interview'})); render(<ApplicationsClient />);
    expect(await screen.findByText('Engineer a')).toHaveAttribute('href', '/applications/a');
    expect(screen.getByText('Interested', {selector:'span'})).toBeInTheDocument(); expect(screen.getByText('Prepare interview')).toBeInTheDocument();
    expect(screen.getByText(/Job: CLOSED/)).toBeInTheDocument(); expect(screen.getByText(/Created:/)).toBeInTheDocument();
    expect(screen.getByRole('link', {name: 'View job'})).toHaveAttribute('href', '/jobs/job-a');
  });
  it('filters on the server and ignores late list responses', async () => {
    const old = deferred<ApplicationListResponse>(); api.listApplications.mockReturnValueOnce(old.promise).mockResolvedValue(list(application('b', 'APPLIED')));
    render(<ApplicationsClient />); fireEvent.change(screen.getByLabelText('Filter by status'), {target: {value: 'APPLIED'}});
    await screen.findByText('Engineer b'); await act(async () => old.resolve(list(application())));
    expect(screen.queryByText('Engineer a')).not.toBeInTheDocument();
    expect(api.listApplications).toHaveBeenLastCalledWith({status: 'APPLIED', limit: 20, offset: 0}, expect.any(AbortSignal));
  });
  it('retries failures visibly', async () => {
    api.listApplications.mockRejectedValueOnce(new Error('List unavailable')); render(<ApplicationsClient />);
    expect(await screen.findByRole('alert')).toHaveTextContent('List unavailable');
    fireEvent.click(screen.getByRole('button', {name: 'Retry applications'})); await screen.findByText('No applications tracked yet.');
  });
  it('paginates with server offsets', async () => {
    api.listApplications.mockResolvedValue({...list(application()), total: 21}); render(<ApplicationsClient />);
    fireEvent.click(await screen.findByRole('button', {name: 'Next'}));
    await waitFor(() => expect(api.listApplications).toHaveBeenLastCalledWith({status: undefined, limit: 20, offset: 20}, expect.any(AbortSignal)));
  });
});

describe('Application management', () => {
  it('loads authoritative detail and only real chronological history', async () => {
    api.getApplication.mockResolvedValue({...application('a', 'APPLIED'), status_history: [
      {id: 'h1', application_id: 'a', from_status: 'INTERESTED', to_status: 'APPLYING', changed_at: '2026-10-01T12:00:00Z'},
      {id: 'h2', application_id: 'a', from_status: 'APPLYING', to_status: 'APPLIED', changed_at: '2026-10-02T12:00:00Z'},
    ]}); render(<ApplicationDetailClient applicationId="a" />);
    await screen.findByText('Engineer a'); expect(screen.getAllByRole('listitem').map(el => el.textContent)).toEqual([expect.stringContaining('Interested → Applying'), expect.stringContaining('Applying → Applied')]);
    expect(screen.getByRole('link', {name: 'View job'})).toHaveAttribute('href', '/jobs/job-a');
    expect(screen.queryByText(/Discovered/)).not.toBeInTheDocument();
  });
  it('updates status despite CLOSED job, excludes current/invalid choices and prevents duplicate saves', async () => {
    const pending = deferred<Application>(); api.updateApplicationStatus.mockReturnValue(pending.promise);
    render(<ApplicationDetailClient applicationId="a" />); await screen.findByText('Engineer a');
    expect(screen.queryByRole('option', {name: 'Interested'})).not.toBeInTheDocument(); expect(screen.queryByRole('option', {name: 'Offer'})).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('New status'), {target:{value:'APPLIED'}});
    const button = screen.getByRole('button', {name: 'Update status'}); fireEvent.click(button); fireEvent.click(button);
    expect(api.updateApplicationStatus).toHaveBeenCalledTimes(1); expect(screen.getByRole('button', {name: 'Save notes'})).toBeDisabled();
    await act(async () => pending.resolve(application('a','APPLIED')));
    expect(screen.getByText('Applied')).toBeInTheDocument(); expect(screen.getByRole('option', {name:'Interview'})).toBeInTheDocument();
  });
  it('retains prior status when backend rejects a transition', async () => {
    api.updateApplicationStatus.mockRejectedValue(new ApiError(422, 'Transition not allowed', 'INVALID_STATUS_TRANSITION'));
    render(<ApplicationDetailClient applicationId="a" />); await screen.findByText('Engineer a');
    fireEvent.change(screen.getByLabelText('New status'), {target:{value:'APPLIED'}}); fireEvent.click(screen.getByRole('button', {name:'Update status'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Status update rejected'); expect(screen.getByText('Interested')).toBeInTheDocument();
  });
  it.each([['add', null, 'First'], ['edit','First','Edited'], ['clear','First','']])('%s notes using authoritative PATCH and 5000 character validation', async (_operation, initial, draft) => {
    api.getApplication.mockResolvedValue({...application(),notes:initial}); api.updateApplicationNotes.mockResolvedValue({...application(),notes:draft || null});
    render(<ApplicationDetailClient applicationId="a" />); await screen.findByText('Engineer a');
    const notes = screen.getByLabelText('Notes'); expect(notes).toHaveAttribute('maxlength','5000');
    fireEvent.change(notes, {target:{value:draft}}); fireEvent.click(screen.getByRole('button', {name:'Save notes'}));
    await waitFor(() => expect(api.updateApplicationNotes).toHaveBeenCalledWith('a',draft || null,expect.any(AbortSignal)));
    await waitFor(() => expect(screen.getByRole('button', {name:'Save notes'})).toBeEnabled()); expect(notes).toHaveValue(draft);
    expect(screen.getByText('No status changes yet.')).toBeInTheDocument();
  });
  it('shows transient notes feedback only after the backend save succeeds', async () => {
    const pending = deferred<Application>(); api.updateApplicationNotes.mockReturnValue(pending.promise);
    render(<ApplicationDetailClient applicationId="a" />); await screen.findByText('Engineer a');
    vi.useFakeTimers();
    try {
      fireEvent.change(screen.getByLabelText('Notes'), {target:{value:'Saved draft'}});
      fireEvent.click(screen.getByRole('button', {name:'Save notes'}));
      expect(screen.queryByText('Notes saved')).not.toBeInTheDocument();
      expect(screen.getByLabelText('Notes')).toBeDisabled();
      await act(async () => pending.resolve({...application(), notes:'Saved draft'}));
      expect(screen.getByRole('alert')).toHaveTextContent('Notes saved');
      expect(screen.getByLabelText('Notes')).toHaveValue('Saved draft');
      expect(screen.getByRole('button', {name:'Save notes'})).toBeEnabled();
      act(() => vi.advanceTimersByTime(5000));
      expect(screen.queryByText('Notes saved')).not.toBeInTheDocument();
    } finally { vi.useRealTimers(); }
  });
  it('preserves unsaved notes on failure', async () => {
    api.updateApplicationNotes.mockRejectedValue(new Error('Notes unavailable')); render(<ApplicationDetailClient applicationId="a" />); await screen.findByText('Engineer a');
    fireEvent.change(screen.getByLabelText('Notes'), {target:{value:'Keep draft'}}); fireEvent.click(screen.getByRole('button', {name:'Save notes'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Notes unavailable'); expect(screen.getByLabelText('Notes')).toHaveValue('Keep draft');
    expect(screen.queryByText('Notes saved')).not.toBeInTheDocument();
  });
  it('requires confirmation, allows cancellation and returns to list after deletion', async () => {
    api.deleteApplication.mockResolvedValue(undefined); render(<ApplicationDetailClient applicationId="a" />); await screen.findByText('Engineer a');
    fireEvent.click(screen.getByRole('button', {name:'Remove application'})); expect(api.deleteApplication).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', {name:'Cancel'})); expect(screen.queryByRole('button', {name:'Confirm removal'})).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', {name:'Remove application'})); fireEvent.click(screen.getByRole('button', {name:'Confirm removal'}));
    await waitFor(() => expect(router.push).toHaveBeenCalledWith('/applications')); expect(api.deleteApplication).toHaveBeenCalledTimes(1); expect(router.refresh).toHaveBeenCalled();
  });
  it('keeps application and confirmation when deletion fails', async () => {
    api.deleteApplication.mockRejectedValue(new Error('Delete failed')); render(<ApplicationDetailClient applicationId="a" />); await screen.findByText('Engineer a');
    fireEvent.click(screen.getByRole('button', {name:'Remove application'})); fireEvent.click(screen.getByRole('button', {name:'Confirm removal'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Delete failed'); expect(screen.getByText('Engineer a')).toBeInTheDocument(); expect(router.push).not.toHaveBeenCalled();
  });
  it('handles owned missing detail without exposing controls', async () => {
    api.getApplication.mockRejectedValue(new ApiError(404,'Missing','APPLICATION_NOT_FOUND')); render(<ApplicationDetailClient applicationId="a" />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Application not found'); expect(screen.queryByLabelText('Notes')).not.toBeInTheDocument();
  });
  it('ignores late detail/history after selecting another application', async () => {
    const old = deferred<Application>(); api.getApplication.mockReturnValueOnce(old.promise).mockResolvedValueOnce(application('b'));
    const view = render(<ApplicationDetailClient applicationId="a" />); view.rerender(<ApplicationDetailClient applicationId="b" />); await screen.findByText('Engineer b');
    await act(async () => old.resolve(application())); expect(screen.queryByText('Engineer a')).not.toBeInTheDocument();
  });
  it.each(['status','notes','delete'])('ignores late %s mutation after navigation', async kind => {
    api.getApplication.mockResolvedValueOnce(application()).mockResolvedValueOnce(application('b'));
    const old = deferred<Application>(); api.updateApplicationStatus.mockReturnValue(old.promise); api.updateApplicationNotes.mockReturnValue(old.promise); api.deleteApplication.mockReturnValue(old.promise);
    const view = render(<ApplicationDetailClient applicationId="a" />); await screen.findByText('Engineer a');
    if (kind === 'status') {fireEvent.change(screen.getByLabelText('New status'),{target:{value:'APPLIED'}}); fireEvent.click(screen.getByRole('button',{name:'Update status'}));}
    if (kind === 'notes') fireEvent.click(screen.getByRole('button',{name:'Save notes'}));
    if (kind === 'delete') {fireEvent.click(screen.getByRole('button',{name:'Remove application'}));fireEvent.click(screen.getByRole('button',{name:'Confirm removal'}));}
    view.rerender(<ApplicationDetailClient applicationId="b" />); await screen.findByText('Engineer b');
    await act(async () => old.resolve(application('a','APPLIED'))); expect(screen.queryByText('Engineer a')).not.toBeInTheDocument(); expect(router.push).not.toHaveBeenCalled();
  });
});

describe('Job tracking', () => {
  it('tracks without match/AI dependencies and reopens persisted tracking', async () => {
    const view = render(<ApplicationTrackingPanel jobId="job-a" />);
    const button = await screen.findByRole('button',{name:'Track Application'}); fireEvent.click(button); fireEvent.click(button);
    expect(await screen.findByRole('link',{name:'Manage application'})).toHaveAttribute('href','/applications/a');
    expect(api.createApplication).toHaveBeenCalledTimes(1); expect(api.createApplication).toHaveBeenCalledWith('job-a',expect.any(AbortSignal));
    view.unmount(); api.listApplications.mockResolvedValue(list(application('a','INTERVIEW'))); render(<ApplicationTrackingPanel jobId="job-a" />);
    expect(await screen.findByText('Interview')).toBeInTheDocument(); expect(screen.queryByRole('button',{name:'Track Application'})).not.toBeInTheDocument();
  });
  it('recovers duplicate 409 through owned job lookup', async () => {
    api.createApplication.mockRejectedValue(new ApiError(409,'Already tracked','APPLICATION_ALREADY_EXISTS'));
    api.listApplications.mockResolvedValueOnce(list()).mockResolvedValueOnce(list(application())); render(<ApplicationTrackingPanel jobId="job-a" />);
    fireEvent.click(await screen.findByRole('button',{name:'Track Application'})); await screen.findByRole('link',{name:'Manage application'});
    expect(screen.queryByRole('alert')).not.toBeInTheDocument(); expect(api.listApplications).toHaveBeenLastCalledWith({job_id:'job-a',limit:1},expect.any(AbortSignal));
  });
  it('reports lookup errors instead of assuming untracked and retries', async () => {
    api.listApplications.mockRejectedValueOnce(new Error('Lookup failed')); render(<ApplicationTrackingPanel jobId="job-a" />);
    await screen.findByRole('alert'); expect(screen.queryByRole('button',{name:'Track Application'})).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Retry tracking'})); await screen.findByRole('button',{name:'Track Application'});
  });
  it('reports creation errors while preserving retry', async () => {
    api.createApplication.mockRejectedValue(new ApiError(404,'Job not found','JOB_NOT_FOUND')); render(<ApplicationTrackingPanel jobId="job-a" />);
    fireEvent.click(await screen.findByRole('button',{name:'Track Application'})); expect(await screen.findByRole('alert')).toHaveTextContent('Job not found');
  });
  it('ignores late job lookup after navigation', async () => {
    const old = deferred<ApplicationListResponse>(); api.listApplications.mockReturnValueOnce(old.promise).mockResolvedValueOnce(list());
    const view = render(<ApplicationTrackingPanel jobId="job-a" />); view.rerender(<ApplicationTrackingPanel jobId="job-b" />);
    await screen.findByRole('button',{name:'Track Application'}); await act(async () => old.resolve(list(application())));
    expect(screen.queryByRole('link',{name:'Manage application'})).not.toBeInTheDocument();
  });
  it('ignores late creation after job navigation', async () => {
    const old = deferred<Application>(); api.createApplication.mockReturnValue(old.promise);
    const view = render(<ApplicationTrackingPanel jobId="job-a" />); fireEvent.click(await screen.findByRole('button',{name:'Track Application'}));
    view.rerender(<ApplicationTrackingPanel jobId="job-b" />); await screen.findByRole('button',{name:'Track Application'});
    await act(async () => old.resolve(application())); expect(screen.queryByRole('link',{name:'Manage application'})).not.toBeInTheDocument();
  });
});
