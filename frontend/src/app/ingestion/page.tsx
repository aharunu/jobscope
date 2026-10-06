'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { ingestionApi, Policy, Mode, PolicyMode, Run, Source, SourceRun, Decision } from '@/lib/api/ingestion';
import { COUNTRY_CODES } from '@/lib/ingestion-countries';
import './ingestion.css';

const active = (run: Run | null) => !!run && ['PENDING', 'RUNNING'].includes(run.status);
const initialPolicy: Policy = { allowed_country_codes: ['TR'], include_unknown_country: false, enabled: true };
const countryNames = new Intl.DisplayNames(['en'], { type: 'region' });
const counts = ['discovered', 'accepted', 'rejected', 'created', 'updated', 'unchanged', 'closed'] as const;

function Status({ value }: { value: string }) {
  return <span className={`ingestion-status ingestion-status-${value.toLowerCase()}`}>{value}</span>;
}

function PolicyFields({ value, onChange }: { value: Policy; onChange: (v: Policy) => void }) {
  return <div className="ingestion-policy">
    <label>Allowed countries<select aria-label="Allowed countries" multiple value={value.allowed_country_codes} onChange={e => onChange({ ...value, allowed_country_codes: Array.from(e.target.selectedOptions, o => o.value) })}>
      {COUNTRY_CODES.map(code => <option key={code} value={code}>{countryNames.of(code)} ({code})</option>)}
    </select></label>
    <p className="text-muted">Use Ctrl/Cmd to select several countries. Empty selection means no country filter.</p>
    <label><input type="checkbox" checked={value.include_unknown_country} onChange={e => onChange({ ...value, include_unknown_country: e.target.checked })} /> Include jobs with unknown country</label>
    <label><input type="checkbox" checked={value.enabled} onChange={e => onChange({ ...value, enabled: e.target.checked })} /> Enable policy</label>
  </div>;
}

export default function IngestionPage() {
  const [catalog, setCatalog] = useState<Source[]>([]);
  const [history, setHistory] = useState<Run[]>([]);
  const [runId, setRunId] = useState('');
  const [run, setRun] = useState<Run | null>(null);
  const [sourceRuns, setSourceRuns] = useState<SourceRun[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [total, setTotal] = useState(0);
  const [mode, setMode] = useState<Mode>('PREVIEW');
  const [policyMode, setPolicyMode] = useState<PolicyMode>('OVERRIDE_SELECTED_SOURCES');
  const [policy, setPolicy] = useState<Policy>(initialPolicy);
  const [policyTarget, setPolicyTarget] = useState('');
  const [hasPolicy, setHasPolicy] = useState(false);
  const [scope, setScope] = useState('all');
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [ats, setAts] = useState('');
  const [activeOnly, setActiveOnly] = useState(true);
  const [decisionFilter, setDecisionFilter] = useState('');
  const [decisionSource, setDecisionSource] = useState('');
  const [reason, setReason] = useState('');
  const [country, setCountry] = useState('');
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const submission = useRef(false);
  const reportError = (err: unknown) => setError(err instanceof Error ? err.message : 'Request failed. Please try again.');

  useEffect(() => {
    let mounted = true;
    Promise.all([ingestionApi.catalog(), ingestionApi.runs(), ingestionApi.defaultPolicy()]).then(([sources, runs, saved]) => {
      if (!mounted) return;
      setCatalog(sources); setHistory(runs.items);
      if (runs.items.length) setRunId(runs.items[0].id);
      if (saved) { setPolicy(saved); setHasPolicy(true); setPolicyMode('USE_SAVED_POLICIES'); }
    }).catch(err => { if (mounted) reportError(err); });
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    let mounted = true;
    const request = policyTarget ? ingestionApi.sourcePolicy(policyTarget) : ingestionApi.defaultPolicy();
    request.then(saved => { if (mounted) { setPolicy(saved || initialPolicy); setHasPolicy(!!saved); } }).catch(err => { if (mounted) reportError(err); });
    return () => { mounted = false; };
  }, [policyTarget]);

  useEffect(() => {
    if (!runId) return;
    let mounted = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const [detail, sources] = await Promise.all([ingestionApi.run(runId), ingestionApi.sources(runId)]);
        if (!mounted) return;
        setRun(detail); setSourceRuns(sources.items);
        if (active(detail)) timer = setTimeout(poll, 1500);
        else ingestionApi.runs().then(r => { if (mounted) setHistory(r.items); }).catch(reportError);
      } catch (err) { if (mounted) { reportError(err); timer = setTimeout(poll, 3000); } }
    };
    setSourceRuns([]); setOffset(0);
    void poll();
    return () => { mounted = false; clearTimeout(timer); };
  }, [runId]);

  const loadDecisions = useCallback(async () => {
    if (!runId) return;
    return ingestionApi.decisions(runId, { decision: decisionFilter || undefined, source_id: decisionSource || undefined, reason: reason || undefined, country: country || undefined, limit: 25, offset });
  }, [runId, decisionFilter, decisionSource, reason, country, offset]);
  useEffect(() => {
    let mounted = true;
    loadDecisions().then(result => { if (mounted && result) { setDecisions(result.items); setTotal(result.total); } }).catch(err => { if (mounted) reportError(err); });
    return () => { mounted = false; };
  }, [loadDecisions, run?.sources_completed]);

  async function action(work: () => Promise<void>) {
    if (submission.current) return;
    submission.current = true; setBusy(true); setError(''); setNotice('');
    try { await work(); } catch (err) { reportError(err); }
    finally { submission.current = false; setBusy(false); }
  }
  async function start() {
    await action(async () => {
      const started = await ingestionApi.start({ mode, policy_mode: policyMode, active_sources_only: activeOnly,
        ...(scope === 'sources' ? { source_ids: selectedSources } : {}), ...(scope === 'ats' ? { ats_types: [ats] } : {}),
        ...(policyMode === 'OVERRIDE_SELECTED_SOURCES' ? { allowed_country_codes: policy.enabled ? policy.allowed_country_codes : [], include_unknown_country: policy.include_unknown_country } : {}) });
      setRun(started); setRunId(started.id); setHistory(old => [started, ...old]);
    });
  }

  return <main className="container ingestion-page">
    <h1>Ingestion Control Center</h1>
    <p className="text-muted">Acquire complete boards, then decide which jobs enter JobScope. Preview changes no canonical jobs.</p>
    {error && <Alert variant="danger">{error}</Alert>}
    {notice && <Alert>{notice}</Alert>}
    <section className="ingestion-card" aria-label="Run configuration">
      <h2>New run</h2>
      <div className="ingestion-grid">
        <label>Mode<select aria-label="Mode" value={mode} onChange={e => setMode(e.target.value as Mode)}><option value="PREVIEW">Preview</option><option value="PERSIST">Persist accepted jobs</option></select></label>
        <label>Scope<select aria-label="Scope" value={scope} onChange={e => setScope(e.target.value)}><option value="all">All sources</option><option value="ats">ATS type</option><option value="sources">Selected sources</option></select></label>
        {scope === 'ats' && <label>ATS<select aria-label="ATS type" value={ats} onChange={e => setAts(e.target.value)}><option value="">Choose ATS</option>{Array.from(new Set(catalog.map(s => s.ats_type))).sort().map(v => <option key={v}>{v}</option>)}</select></label>}
        {scope === 'sources' && <label>Sources<select aria-label="Selected sources" multiple value={selectedSources} onChange={e => setSelectedSources(Array.from(e.target.selectedOptions, o => o.value))}>{catalog.map(s => <option key={s.id} value={s.id}>{s.name} · {s.ats_type}{s.active ? '' : ' · inactive'}</option>)}</select></label>}
        <label>Policy mode<select aria-label="Policy mode" value={policyMode} onChange={e => setPolicyMode(e.target.value as PolicyMode)}><option value="OVERRIDE_SELECTED_SOURCES">Override for this run</option><option value="USE_SAVED_POLICIES">Use saved policies</option></select></label>
      </div>
      <label><input type="checkbox" checked={activeOnly} onChange={e => setActiveOnly(e.target.checked)} /> Active sources only</label>
      {policyMode === 'OVERRIDE_SELECTED_SOURCES' && <PolicyFields value={policy} onChange={setPolicy} />}
      {policyMode === 'USE_SAVED_POLICIES' && <p>Source override → global default → no filter. Saved policies are snapshotted when the run starts.</p>}
      {mode === 'PERSIST' && <Alert variant="warning">Accepted jobs will be persisted. An active country filter suppresses absence closure; historical jobs are retained.</Alert>}
      <Button onClick={start} isLoading={busy} disabled={active(run) || (scope === 'sources' && !selectedSources.length) || (scope === 'ats' && !ats)}>Start {mode === 'PREVIEW' ? 'preview' : 'persist'}</Button>
    </section>
    <section className="ingestion-card" aria-label="Policy editor">
      <h2>Saved policies</h2>
      <label>Policy target<select aria-label="Policy target" value={policyTarget} onChange={e => setPolicyTarget(e.target.value)}><option value="">Global default</option>{catalog.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
      <p>{hasPolicy ? 'Saved policy exists' : policyTarget ? 'No override: inherits global default' : 'No global default saved. Turkey is suggested; save explicitly to enable it.'}</p>
      <PolicyFields value={policy} onChange={setPolicy} />
      <div className="ingestion-actions"><Button disabled={busy} onClick={() => action(async () => { const saved = policyTarget ? await ingestionApi.saveSource(policyTarget, policy) : await ingestionApi.saveDefault(policy); setPolicy(saved); setHasPolicy(true); setNotice('Policy saved'); })}>Save policy</Button>
      {policyTarget && <Button variant="secondary" disabled={busy || !hasPolicy} onClick={() => action(async () => { await ingestionApi.deleteSource(policyTarget); setHasPolicy(false); setPolicy(initialPolicy); setNotice('Override removed. This source now inherits the global default.'); })}>Remove override</Button>}</div>
    </section>
    <section className="ingestion-card">
      <h2>Run monitor</h2>
      <label>Run history<select aria-label="Run history" value={runId} onChange={e => setRunId(e.target.value)}><option value="">Choose run</option>{history.map(r => <option key={r.id} value={r.id}>{r.mode} · {r.status} · {new Date(r.created_at).toLocaleString()}</option>)}</select></label>
      {run && <>
        <p><strong>{run.mode} · <Status value={run.status} /></strong>{run.cancel_requested_at && ' · cancellation requested'}</p>
        <progress aria-label="Run progress" max={100} value={run.progress?.percentage || 0} />
        <p>{run.sources_completed} / {run.sources_total} sources · {run.progress?.percentage || 0}% · {run.progress?.current_source_name || 'No current source'}</p>
        <p>Succeeded {run.progress?.sources_succeeded || 0} · Partial {run.progress?.sources_partial || 0} · Failed {run.progress?.sources_failed || 0}</p>
        <div className="ingestion-counts">{counts.map(k => <span key={k}>{k}: <strong>{run[`jobs_${k}`]}</strong></span>)}</div>
        {run.mode === 'PREVIEW' && ['COMPLETED', 'COMPLETED_WITH_WARNINGS'].includes(run.status) && <>
          <p>The same sources will be fetched again using this preview’s saved policy snapshots. Live jobs may have changed. Accepted jobs will be persisted; existing closure safeguards apply.</p>
          <Button disabled={busy} onClick={() => action(async () => {
            const started = await ingestionApi.start({ mode: 'PERSIST', from_preview_run_id: run.id });
            setRun(started); setRunId(started.id); setHistory(old => [started, ...old]);
          })}>Persist this preview</Button>
        </>}
        {active(run) && <Button variant="secondary" disabled={busy || !!run.cancel_requested_at} onClick={() => action(async () => { setRun(await ingestionApi.cancel(run.id)); })}>Cancel after current source</Button>}
      </>}
      {sourceRuns.map(s => <details key={s.id}><summary>{s.source_name} · {s.ats_type} · <Status value={s.status} /> · accepted {s.jobs_accepted} / discovered {s.jobs_discovered}</summary>
        <div className="ingestion-counts">{counts.map(k => <span key={k}>{k}: {s[`jobs_${k}`]}</span>)}</div>
        <p>{Math.round(s.duration_ms)} ms · acquisition complete: {String(s.acquisition_complete)} · closure authorized: {String(s.closure_authorized)}</p>
        <p>Closure: {s.closure_suppression_reason || 'Authorized by existing lifecycle guards'}</p>
        <p>Policy: {s.policy_snapshot.origin} · {s.policy_snapshot.enabled ? s.policy_snapshot.allowed_country_codes.join(', ') || 'No filter' : 'Disabled'} · unknown included: {String(s.policy_snapshot.include_unknown_country)}</p>
        <p>Warnings ({s.warning_count}): {s.warnings.join('; ') || 'None'}</p>{s.error_type && <Alert variant="danger">{s.error_type}: {s.error_message}</Alert>}
      </details>)}
    </section>
    {runId && <section className="ingestion-card">
      <h2>Decisions</h2><p>Compact audit only; rejected job content is not persisted.</p>
      <div className="ingestion-grid">
        <label>Decision<select aria-label="Decision filter" value={decisionFilter} onChange={e => { setDecisionFilter(e.target.value); setOffset(0); }}><option value="">All</option><option>ACCEPTED</option><option>REJECTED</option></select></label>
        <label>Source<select aria-label="Decision source" value={decisionSource} onChange={e => { setDecisionSource(e.target.value); setOffset(0); }}><option value="">All</option>{sourceRuns.map(s => <option key={s.id} value={s.source_id}>{s.source_name}</option>)}</select></label>
        <label>Reason<select aria-label="Reason filter" value={reason} onChange={e => { setReason(e.target.value); setOffset(0); }}><option value="">All</option>{['COUNTRY_ALLOWED', 'COUNTRY_NOT_ALLOWED', 'COUNTRY_UNKNOWN', 'UNKNOWN_INCLUDED', 'NO_COUNTRY_FILTER', 'INVALID_DISCOVERED_JOB'].map(r => <option key={r}>{r}</option>)}</select></label>
        <label>Country<select aria-label="Decision country" value={country} onChange={e => { setCountry(e.target.value); setOffset(0); }}><option value="">All</option>{COUNTRY_CODES.map(c => <option key={c} value={c}>{countryNames.of(c)}</option>)}</select></label>
      </div>
      <div className="ingestion-table"><table><thead><tr><th>Job</th><th>Source</th><th>Location</th><th>Country</th><th>Decision</th><th>Reason</th></tr></thead><tbody>{decisions.map(d => <tr key={d.id}><td>{d.canonical_url.startsWith('https://') || d.canonical_url.startsWith('http://') ? <a href={d.canonical_url} target="_blank" rel="noreferrer">{d.title || 'Untitled'}</a> : d.title || 'Untitled'}</td><td>{sourceRuns.find(s => s.source_id === d.source_id)?.source_name || d.source_id}</td><td>{d.location || 'Unknown'}</td><td>{d.resolved_country || 'UNKNOWN'}</td><td>{d.decision}</td><td>{d.reason}</td></tr>)}</tbody></table></div>
      <div className="ingestion-actions"><Button variant="secondary" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 25))}>Previous</Button><span>{total} decisions · page {Math.floor(offset / 25) + 1}</span><Button variant="secondary" disabled={offset + 25 >= total} onClick={() => setOffset(offset + 25)}>Next</Button></div>
    </section>}
  </main>;
}
