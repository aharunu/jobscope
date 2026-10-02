'use client';

import React, {useEffect, useRef, useState} from 'react';
import {analyzeMatch} from '@/lib/api/matching';
import type {MatchResultResponse} from '@/lib/api/types';
import {Alert} from '@/components/ui/Alert';
import {Button} from '@/components/ui/Button';

export function AIAnalysisPanel({match, onResult, disabled = false}: {match: MatchResultResponse; onResult: (result: MatchResultResponse) => void; disabled?: boolean}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lock = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const mounted = useRef(true);
  const retryForce = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => {mounted.current = false; controller.current?.abort();};
  }, []);
  const request = async (force: boolean) => {
    if (disabled || lock.current) return;
    lock.current = true; setBusy(true); setError(null); retryForce.current = force;
    const current = new AbortController(); controller.current = current;
    try {
      const result = await analyzeMatch(match.id, force, current.signal);
      if (!mounted.current || current.signal.aborted) return;
      if (result.id !== match.id || result.job_id !== match.job_id || result.search_profile_id !== match.search_profile_id) throw new Error('AI result does not belong to this match.');
      onResult(result);
    } catch (err) {
      if (mounted.current && !current.signal.aborted) setError(err instanceof Error ? err.message : 'AI analysis could not be completed.');
    } finally {
      if (mounted.current && !current.signal.aborted) {lock.current = false; setBusy(false);}
    }
  };
  const analysis = match.ai_analysis;
  return <section className="ai-analysis" aria-label="Optional AI analysis">
    <h3>Optional AI Analysis</h3>
    <p className="text-muted">An explicit analysis sends this job, relevant profile and search preferences to the configured AI provider. Saved analysis can become stale after edits.</p>
    <Button disabled={busy || disabled} onClick={() => request(Boolean(analysis))}>{busy ? 'Analyzing...' : analysis ? 'Re-analyze AI' : 'AI ile Detaylı Analiz Et'}</Button>
    {busy && <p role="status">Analyzing supplied evidence. Deterministic result remains available.</p>}
    {error && <><Alert variant="danger">{error} Deterministic match is still available.</Alert><Button disabled={busy || disabled} onClick={() => request(retryForce.current)}>Retry AI Analysis</Button></>}
    {analysis && <>
      <p role="status">{analysis.cached ? 'Saved AI analysis' : 'AI analysis completed'}</p>
      <dl className="ai-scores">
        <div><dt>Deterministic Score</dt><dd>{Number(match.deterministic_score).toFixed(2)}</dd></div>
        <div><dt>AI Score</dt><dd>{Number(match.ai_score).toFixed(2)}</dd></div>
        <div><dt>AI Adjustment</dt><dd>{Number(match.ai_adjustment) >= 0 ? '+' : ''}{Number(match.ai_adjustment).toFixed(2)}</dd></div>
        <div><dt>Final Score</dt><dd>{Number(match.final_score).toFixed(2)}</dd></div>
        <div><dt>Confidence</dt><dd>{Number(match.confidence).toFixed(2)}%</dd></div>
      </dl>
      <p>{analysis.assessment} · {analysis.provider} / {analysis.model}{analysis.created_at ? ` · ${new Date(analysis.created_at).toLocaleString()}` : ''}</p>
      <h4>Summary</h4><p>{analysis.summary}</p>
      {(['strengths', 'gaps', 'risks'] as const).map(section => <div key={section}><h4>{section[0].toUpperCase() + section.slice(1)}</h4>{analysis[section].length ? <ul>{analysis[section].map((item, i) => <li key={i}>{item}</li>)}</ul> : <p className="text-muted">None reported.</p>}</div>)}
      <h4>Evidence</h4>
      {!analysis.evidence.length && <p>Insufficient Evidence</p>}
      {analysis.evidence.map(item => <article className="profile-entry" key={item.id}><strong>{item.claim}</strong><p>{item.source_reference === 'INSUFFICIENT_EVIDENCE' ? 'Insufficient Evidence' : `${item.evidence_type}: ${item.source_reference}`}</p>{item.source_quote && <blockquote>{item.source_quote}</blockquote>}<p>{item.reason}</p></article>)}
      <p className="text-muted">AI influence is bounded to ±8 points. Unsupported evidence cannot adjust the score; deterministic blockers remain in force.</p>
    </>}
  </section>;
}
