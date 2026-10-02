'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import { ApiError, type SearchProfileResponse, type MatchResultResponse } from '@/lib/api/types';
import { evaluateMatch, getSavedMatch } from '@/lib/api/matching';
import { SearchProfileSelector } from '@/components/search_profile/SearchProfileSelector';
import { ScoreGauge } from './ScoreGauge';
import { BlockerAlert } from './BlockerAlert';
import { CategoryScoresBreakdown } from './CategoryScoresBreakdown';
import { SkillsEvidenceList } from './SkillsEvidenceList';
import { RequirementMatchesList } from './RequirementMatchesList';
import { Alert } from '@/components/ui/Alert';
import {AIAnalysisPanel} from './AIAnalysisPanel';

interface MatchPanelProps {
  jobId: string;
  searchProfiles: SearchProfileResponse[];
  selectedProfileId: string;
  onSelectProfile: (profileId: string) => void;
  initialMatchResult?: MatchResultResponse | null;
}

export function MatchPanel({jobId, searchProfiles, selectedProfileId, onSelectProfile, initialMatchResult = null}: MatchPanelProps) {
  const key = `${jobId}:${selectedProfileId}`;
  const [matchCache, setMatchCache] = useState<Record<string, MatchResultResponse>>(() =>
    initialMatchResult?.job_id === jobId && initialMatchResult.search_profile_id === selectedProfileId
      ? {[key]: initialMatchResult} : {});
  const [loading, setLoading] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [retryCalculation, setRetryCalculation] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);
  const requestVersion = useRef(0);
  const busy = useRef(false);
  const selection = useRef(key);
  selection.current = key;
  const currentMatch = selectedProfileId ? matchCache[key] ?? null : null;

  const performRequest = useCallback(async (profileId: string, calculate: boolean) => {
    if (!profileId || (calculate && busy.current)) return;
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    const version = ++requestVersion.current;
    const requestKey = `${jobId}:${profileId}`;
    busy.current = true;
    setLoading(true); setCalculating(calculate); setError(null); setErrorStatus(null);
    setRetryCalculation(calculate);
    const active = () => version === requestVersion.current && selection.current === requestKey && !controller.signal.aborted;
    try {
      const result = calculate
        ? await evaluateMatch({job_id: jobId, search_profile_id: profileId}, controller.signal)
        : await getSavedMatch(jobId, profileId, controller.signal);
      if (active()) {
        if (result.job_id !== jobId || result.search_profile_id !== profileId) throw new Error('Received a result for a different job or profile.');
        setMatchCache(prev => ({...prev, [requestKey]: result}));
      }
    } catch (err) {
      if (!active()) return;
      if (!calculate && err instanceof ApiError && err.code === 'MATCH_RESULT_NOT_FOUND') {
        setMatchCache(prev => {const next = {...prev}; delete next[requestKey]; return next;});
      } else {
        setError(err instanceof Error ? err.message : 'Could not load match result.');
        setErrorStatus(err instanceof ApiError ? err.status : 500);
      }
    } finally {
      if (active()) {busy.current = false; setLoading(false); setCalculating(false);}
    }
  }, [jobId]);

  useEffect(() => {
    busy.current = false;
    setCalculating(false);
    if (selectedProfileId) void performRequest(selectedProfileId, false);
    else {setLoading(false); setError(null);}
    return () => {++requestVersion.current; controllerRef.current?.abort();};
  }, [jobId, selectedProfileId, performRequest]);

  return <section className="card" style={{padding: '1.5rem', display: 'grid', gap: '1.5rem'}} data-testid="match-panel">
    <div style={{display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem'}}>
      <div><h2>Deterministic Match Evaluation</h2><p className="text-muted">Review your saved calculation or explicitly calculate a new one.</p></div>
      {selectedProfileId && <button className="btn btn-secondary" data-testid="re-evaluate-btn" disabled={loading} onClick={() => performRequest(selectedProfileId, true)}>
        {calculating ? 'Evaluating...' : loading ? 'Loading saved result...' : currentMatch ? '↻ Re-evaluate' : 'Calculate Match'}
      </button>}
    </div>
    <SearchProfileSelector profiles={searchProfiles} selectedProfileId={selectedProfileId} onSelectProfile={onSelectProfile} disabled={calculating} jobId={jobId}/>
    {error && <div data-testid="match-error-container">
      <Alert variant="danger" title={errorStatus === 401 ? 'Authentication Required' : errorStatus === 404 ? 'Resource Not Found' : errorStatus === 422 ? 'Invalid Match Evaluation Request' : 'Match Evaluation Error'}>{error}</Alert>
      <button className="btn btn-secondary" disabled={loading} onClick={() => performRequest(selectedProfileId, retryCalculation)}>{retryCalculation ? 'Retry Match Evaluation' : 'Retry Saved Match'}</button>
    </div>}
    {loading && <p role="status" data-testid="match-loading">{calculating ? 'Evaluating candidate profile against deterministic criteria...' : 'Loading saved match result...'}</p>}
    {!loading && !currentMatch && !error && selectedProfileId && <p role="status">No saved match result yet. Calculate a match when you are ready.</p>}
    {searchProfiles.length === 0 && <div data-testid="match-panel-empty-profiles" role="status">
      <p>No candidate search profiles found. Create a profile to evaluate match suitability.</p>
      <Link href={`/search-profiles/new?returnUrl=/jobs/${encodeURIComponent(jobId)}`} className="btn btn-secondary" data-testid="match-empty-create-profile-btn">Create Search Profile</Link>
    </div>}
    {currentMatch && <div style={{display: 'grid', gap: '1.5rem'}}>
      <p className="text-muted">Saved calculation{currentMatch.updated_at ? ` · ${new Date(currentMatch.updated_at).toLocaleString()}` : ''}. Profile edits do not automatically recalculate it.</p>
      <ScoreGauge overallScore={currentMatch.overall_score} confidence={currentMatch.confidence}/>
      <p>Deterministic Score: {Number(currentMatch.deterministic_score).toFixed(2)}</p>
      <AIAnalysisPanel key={`${key}:${currentMatch.updated_at ?? ''}`} match={currentMatch} disabled={loading} onResult={result => setMatchCache(prev => ({...prev, [key]: result}))}/>
      {!!currentMatch.explanation?.blockers.length && <BlockerAlert blockers={currentMatch.explanation.blockers}/>}
      <div><h3>Category Match Scores</h3><CategoryScoresBreakdown categoryScores={currentMatch.category_scores}/></div>
      <div><h3>Skills Evidence</h3><SkillsEvidenceList explanation={currentMatch.explanation}/></div>
      <div><h3>Requirement Matches &amp; Evidence</h3><RequirementMatchesList requirements={currentMatch.requirement_matches}/></div>
    </div>}
  </section>;
}
