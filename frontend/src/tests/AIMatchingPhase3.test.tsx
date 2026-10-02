import React from 'react';
import {act, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {MatchPanel} from '../components/matching/MatchPanel';
import {ApiError, type MatchResultResponse, type SearchProfileResponse} from '../lib/api/types';

const api = vi.hoisted(() => ({getSavedMatch: vi.fn(), evaluateMatch: vi.fn(), analyzeMatch: vi.fn()}));
vi.mock('../lib/api/matching', () => api);
const profiles = ['a', 'b'].map(id => ({id, name: id, base_profile_id: 'base', target_roles: [], target_skills: [], locations: [], work_modes: [], industries: [], seniority: null, salary_min: null, salary_max: null, created_at: null, updated_at: null})) satisfies SearchProfileResponse[];
const deterministic = (profile = 'a'): MatchResultResponse => ({id: `match-${profile}`, job_id: 'job', search_profile_id: profile, base_profile_id: 'base', overall_score: 86, deterministic_score: 86, final_score: 86, confidence: 70, category_scores: {}, requirement_matches: [], explanation: null, created_at: null, updated_at: '2026-10-01T10:00:00Z'});
const analyzed = (profile = 'a', cached = false): MatchResultResponse => ({...deterministic(profile), overall_score: 88, ai_score: 94, ai_adjustment: 2, final_score: 88, confidence: 77.5, updated_at: '2026-10-02T10:00:00Z', ai_analysis: {id: 'analysis', match_result_id: `match-${profile}`, provider: 'fake', model: 'test-model', ai_score: 94, assessment: 'STRONG', summary: 'Evidence-backed alignment', strengths: ['Python strength'], gaps: ['Rust gap'], risks: ['Location uncertainty'], evidence: [{id:'e1', claim:'Python recorded', evidence_type:'SKILL',source_reference:'profile.skills[0]',source_quote:'Python',reason:'Referenced skill'}, {id:'e2', claim:'Unverified leadership',evidence_type:'NONE',source_reference:'INSUFFICIENT_EVIDENCE',source_quote:null,reason:'Unsupported claim'}],created_at:'2026-10-02T10:00:00Z',cached}});
const props = {jobId:'job',searchProfiles:profiles,selectedProfileId:'a',onSelectProfile:vi.fn()};
const deferred = () => {let resolve!: (value: MatchResultResponse) => void; let reject!: (value: Error) => void; const promise = new Promise<MatchResultResponse>((a,b) => {resolve=a;reject=b;});return {promise,resolve,reject};};

describe('Explicit optional AI matching', () => {
  beforeEach(() => {vi.resetAllMocks();api.getSavedMatch.mockImplementation((_job, profile) => Promise.resolve(deterministic(profile)));api.analyzeMatch.mockResolvedValue(analyzed());});
  it('requires a saved deterministic result and never analyzes on mount or profile switch', async () => {
    api.getSavedMatch.mockRejectedValueOnce(new ApiError(404,'No saved match','MATCH_RESULT_NOT_FOUND'));
    const view = render(<MatchPanel {...props}/>);
    await screen.findByText(/No saved match result yet/);
    expect(screen.queryByRole('button',{name:'AI ile Detaylı Analiz Et'})).not.toBeInTheDocument();
    view.rerender(<MatchPanel {...props} selectedProfileId="b"/>);
    expect(await screen.findByRole('button',{name:'AI ile Detaylı Analiz Et'})).toBeEnabled();
    expect(api.analyzeMatch).not.toHaveBeenCalled();
    expect(api.evaluateMatch).not.toHaveBeenCalled();
  });
  it('only clicks invoke AI, prevents duplicate requests and displays distinct scores and evidence', async () => {
    const request = deferred();api.analyzeMatch.mockReturnValue(request.promise);
    render(<MatchPanel {...props}/>);
    const button = await screen.findByRole('button',{name:'AI ile Detaylı Analiz Et'});
    fireEvent.click(button);fireEvent.click(button);
    expect(api.analyzeMatch).toHaveBeenCalledTimes(1);
    expect(api.analyzeMatch).toHaveBeenCalledWith('match-a',false,expect.any(AbortSignal));
    expect(screen.getByRole('button',{name:'Analyzing...'})).toBeDisabled();
    expect(screen.getByText('86')).toBeInTheDocument();
    await act(async () => {request.resolve(analyzed());});
    const panel = within(screen.getByRole('region',{name:'Optional AI analysis'}));
    expect(await panel.findByText('AI analysis completed')).toBeInTheDocument();
    for (const text of ['Deterministic Score','AI Score','AI Adjustment','Final Score','Confidence','86.00','94.00','+2.00','88.00','77.50%','Evidence-backed alignment','Python strength','Rust gap','Location uncertainty','Python recorded','Insufficient Evidence']) expect(panel.getByText(text)).toBeInTheDocument();
  });
  it('saved AI loads after reopening with no provider action and re-analysis uses force', async () => {
    api.getSavedMatch.mockResolvedValue(analyzed('a',true));
    const view = render(<MatchPanel {...props}/>);
    await screen.findByText('Saved AI analysis');
    expect(api.analyzeMatch).not.toHaveBeenCalled();view.unmount();
    render(<MatchPanel {...props}/>);await screen.findByText('Saved AI analysis');
    expect(api.analyzeMatch).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button',{name:'Re-analyze AI'}));
    await waitFor(() => expect(api.analyzeMatch).toHaveBeenCalledWith('match-a',true,expect.any(AbortSignal)));
  });
  it('provider failures keep deterministic result visible and explicit retry succeeds', async () => {
    api.analyzeMatch.mockRejectedValueOnce(new ApiError(503,'Optional AI provider is not configured.')).mockResolvedValueOnce(analyzed());
    render(<MatchPanel {...props}/>);fireEvent.click(await screen.findByRole('button',{name:'AI ile Detaylı Analiz Et'}));
    expect(await screen.findByText(/Deterministic match is still available/)).toBeInTheDocument();
    expect(screen.getByText('86')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Retry AI Analysis'}));
    await screen.findByText('AI analysis completed');expect(api.analyzeMatch).toHaveBeenCalledTimes(2);
  });
  it.each(['success','failure'])('ignores stale AI %s after profile switching', async outcome => {
    const request = deferred();api.analyzeMatch.mockReturnValue(request.promise);
    const view = render(<MatchPanel {...props}/>);fireEvent.click(await screen.findByRole('button',{name:'AI ile Detaylı Analiz Et'}));
    view.rerender(<MatchPanel {...props} selectedProfileId="b"/>);
    await screen.findByRole('button',{name:'AI ile Detaylı Analiz Et'});
    await act(async () => {outcome==='success'?request.resolve(analyzed()):request.reject(new Error('Old AI failure'));});
    expect(screen.queryByText('Evidence-backed alignment')).not.toBeInTheDocument();
    expect(screen.queryByText(/Old AI failure/)).not.toBeInTheDocument();
    expect(screen.getByText('86')).toBeInTheDocument();
  });
  it('ignores stale AI after deterministic recalculation of the same match identity', async () => {
    const request = deferred();api.analyzeMatch.mockReturnValue(request.promise);
    api.evaluateMatch.mockResolvedValue({...deterministic(),updated_at:'2026-10-02T11:00:00Z'});
    render(<MatchPanel {...props}/>);fireEvent.click(await screen.findByRole('button',{name:'AI ile Detaylı Analiz Et'}));
    fireEvent.click(screen.getByTestId('re-evaluate-btn'));
    await waitFor(() => expect(screen.getByRole('button',{name:'AI ile Detaylı Analiz Et'})).toBeEnabled());
    await act(async () => {request.resolve(analyzed());});
    expect(screen.queryByText('Evidence-backed alignment')).not.toBeInTheDocument();
  });
  it('prevents AI requests while the authoritative saved snapshot is loading', async () => {
    const request = deferred();api.getSavedMatch.mockReturnValue(request.promise);
    render(<MatchPanel {...props} initialMatchResult={deterministic()}/>);
    expect(screen.getByRole('button',{name:'AI ile Detaylı Analiz Et'})).toBeDisabled();
    fireEvent.click(screen.getByRole('button',{name:'AI ile Detaylı Analiz Et'}));
    expect(api.analyzeMatch).not.toHaveBeenCalled();
    await act(async () => {request.resolve(deterministic());});
    expect(screen.getByRole('button',{name:'AI ile Detaylı Analiz Et'})).toBeEnabled();
  });
});
