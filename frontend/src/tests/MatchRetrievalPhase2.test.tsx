import React from 'react';
import {act, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {MatchPanel} from '../components/matching/MatchPanel';
import {ApiError, type MatchResultResponse, type SearchProfileResponse} from '../lib/api/types';

const api = vi.hoisted(() => ({getSavedMatch: vi.fn(), evaluateMatch: vi.fn()}));
vi.mock('../lib/api/matching', () => api);
const profiles = ['a', 'b'].map(id => ({id, name: id, base_profile_id: 'base', target_roles: [], target_skills: [], locations: [], work_modes: [], industries: [], seniority: null, salary_min: null, salary_max: null, created_at: null, updated_at: null})) satisfies SearchProfileResponse[];
const result = (profile = 'a', job = 'job', score = 80): MatchResultResponse => ({id: `match-${profile}`, job_id: job, search_profile_id: profile, base_profile_id: 'base', overall_score: score, deterministic_score: score, final_score: score, confidence: 90, category_scores: {}, requirement_matches: [], explanation: null, created_at: null, updated_at: null});
const props = {jobId: 'job', searchProfiles: profiles, selectedProfileId: 'a', onSelectProfile: vi.fn()};
const missing = () => new ApiError(404, 'No saved match result yet', 'MATCH_RESULT_NOT_FOUND');
const deferred = () => {let resolve!: (value: MatchResultResponse) => void; let reject!: (value: Error) => void; const promise = new Promise<MatchResultResponse>((a, b) => {resolve = a; reject = b;}); return {promise, resolve, reject};};

describe('Persisted match panel lifecycle', () => {
  beforeEach(() => {vi.resetAllMocks(); api.getSavedMatch.mockResolvedValue(result());});
  it('retrieves on mount and revisit without calculating', async () => {
    const view = render(<MatchPanel {...props}/>);
    await screen.findByText('80');
    expect(api.evaluateMatch).not.toHaveBeenCalled();
    view.unmount(); render(<MatchPanel {...props}/>);
    await screen.findByText('80');
    expect(api.getSavedMatch).toHaveBeenCalledTimes(2);
    expect(api.evaluateMatch).not.toHaveBeenCalled();
  });
  it('shows missing state and requires an explicit calculation, preventing double POST', async () => {
    api.getSavedMatch.mockRejectedValue(missing());
    const post = deferred(); api.evaluateMatch.mockReturnValue(post.promise);
    render(<MatchPanel {...props}/>);
    await screen.findByText(/No saved match result yet/);
    expect(api.evaluateMatch).not.toHaveBeenCalled();
    const button = screen.getByRole('button', {name: 'Calculate Match'});
    fireEvent.click(button); fireEvent.click(button);
    expect(api.evaluateMatch).toHaveBeenCalledTimes(1);
    await act(async () => {post.resolve(result());});
    expect(await screen.findByText('80')).toBeInTheDocument();
  });
  it.each(['success', 'failure'])('ignores stale GET %s after switching profiles', async outcome => {
    const old = deferred(); api.getSavedMatch.mockReturnValueOnce(old.promise).mockResolvedValueOnce(result('b', 'job', 60));
    const view = render(<MatchPanel {...props}/>);
    view.rerender(<MatchPanel {...props} selectedProfileId="b"/>);
    await screen.findByText('60');
    await act(async () => {outcome === 'success' ? old.resolve(result()) : old.reject(new Error('Old error'));});
    expect(screen.queryByText('80')).not.toBeInTheDocument();
    expect(screen.queryByText('Old error')).not.toBeInTheDocument();
    expect(api.evaluateMatch).not.toHaveBeenCalled();
  });
  it.each(['success', 'failure'])('ignores stale POST %s after navigation changes the selection', async outcome => {
    api.getSavedMatch.mockResolvedValueOnce(result()).mockResolvedValueOnce(result('b', 'job', 60));
    const old = deferred(); api.evaluateMatch.mockReturnValue(old.promise);
    const view = render(<MatchPanel {...props}/>); await screen.findByText('80');
    fireEvent.click(screen.getByTestId('re-evaluate-btn'));
    view.rerender(<MatchPanel {...props} selectedProfileId="b"/>);
    await screen.findByText('60');
    await act(async () => {outcome === 'success' ? old.resolve(result()) : old.reject(new Error('Old error'));});
    expect(screen.queryByText('80')).not.toBeInTheDocument();
    expect(screen.queryByText('Old error')).not.toBeInTheDocument();
  });
  it('retries retrieval failures with GET and isolates cached jobs', async () => {
    api.getSavedMatch.mockRejectedValueOnce(new ApiError(500, 'Database unavailable')).mockResolvedValueOnce(result()).mockRejectedValueOnce(missing());
    const view = render(<MatchPanel {...props}/>);
    fireEvent.click(await screen.findByRole('button', {name: 'Retry Saved Match'}));
    await screen.findByText('80');
    expect(api.evaluateMatch).not.toHaveBeenCalled();
    view.rerender(<MatchPanel {...props} jobId="other-job"/>);
    await screen.findByText(/No saved match result yet/);
    expect(screen.queryByText('80')).not.toBeInTheDocument();
    await waitFor(() => expect(api.getSavedMatch).toHaveBeenLastCalledWith('other-job', 'a', expect.any(AbortSignal)));
  });
  it('releases calculation controls when the active selection is cleared', async () => {
    api.evaluateMatch.mockReturnValue(deferred().promise);
    const view = render(<MatchPanel {...props}/>); await screen.findByText('80');
    fireEvent.click(screen.getByTestId('re-evaluate-btn'));
    view.rerender(<MatchPanel {...props} selectedProfileId=""/>);
    await waitFor(() => expect(screen.getByRole('combobox')).toBeEnabled());
    expect(screen.queryByTestId('match-loading')).not.toBeInTheDocument();
  });
});
