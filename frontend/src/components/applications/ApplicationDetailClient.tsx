'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { deleteApplication, getApplication, updateApplicationNotes, updateApplicationStatus } from '@/lib/api/applications';
import { ApiError, type Application, type ApplicationStatus } from '@/lib/api/types';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { APPLICATION_TRANSITIONS, ApplicationStatusBadge, applicationDate, statusLabel } from './status';

export function ApplicationDetailClient({applicationId}: {applicationId: string}) {
  return <ApplicationDetail key={applicationId} applicationId={applicationId} />;
}
function ApplicationDetail({applicationId}: {applicationId: string}) {
  const router = useRouter();
  const [app, setApp] = useState<Application | null>(null);
  const [notes, setNotes] = useState('');
  const [notesSaved, setNotesSaved] = useState(false);
  const [target, setTarget] = useState<ApplicationStatus | ''>('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [confirm, setConfirm] = useState(false);
  const [retry, setRetry] = useState(0);
  const controllerRef = useRef<AbortController | null>(null);
  const locked = useRef(false);
  useEffect(() => {
    if (!notesSaved) return;
    const timer = setTimeout(() => setNotesSaved(false), 5000);
    return () => clearTimeout(timer);
  }, [notesSaved]);
  useEffect(() => {
    const controller = new AbortController(); controllerRef.current = controller;
    setLoading(true); setError('');
    getApplication(applicationId, controller.signal).then(result => {
      if (!controller.signal.aborted) { setApp(result); setNotes(result.notes || ''); }
    }).catch(err => {
      if (!controller.signal.aborted) setError(err instanceof ApiError && err.isNotFound ? 'Application not found or unavailable to this user.' : err instanceof Error ? err.message : 'Unable to load application.');
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [applicationId, retry]);
  async function mutate(kind: 'status' | 'notes' | 'delete') {
    const signal = controllerRef.current?.signal;
    if (!app || locked.current || !signal || signal.aborted) return;
    if (kind === 'status' && (!target || target === app.status)) return;
    if (kind === 'notes' && notes.length > 5000) return;
    if (kind === 'delete' && !confirm) return;
    locked.current = true; setBusy(kind); setError(''); setNotesSaved(false);
    try {
      if (kind === 'delete') {
        await deleteApplication(applicationId, signal);
        if (!signal.aborted) { setApp(null); router.push('/applications'); router.refresh(); }
      } else {
        const result = kind === 'status' ? await updateApplicationStatus(applicationId, target as ApplicationStatus, signal) : await updateApplicationNotes(applicationId, notes.trim() || null, signal);
        if (!signal.aborted) {
          setApp(result); setTarget('');
          if (kind === 'notes') { setNotes(result.notes || ''); setNotesSaved(true); }
        }
      }
    } catch (err) {
      if (!signal.aborted) {
        setError(err instanceof ApiError && err.code === 'INVALID_STATUS_TRANSITION' ? `Status update rejected: ${err.message}` : err instanceof ApiError && err.isNotFound ? 'Application not found or unavailable to this user.' : err instanceof Error ? err.message : 'Unable to save application.');
      }
    } finally { locked.current = false; if (!signal.aborted) setBusy(''); }
  }
  return <div className="container application-page">
    <Link href="/applications">← Back to applications</Link>
    {loading && <p role="status">Loading application and history…</p>}
    {error && <Alert variant="danger">{error}</Alert>}
    {!loading && !app && <Button onClick={() => setRetry(v => v + 1)}>Retry application</Button>}
    {!loading && app && <>
      <section className="card application-section">
        <h1>{app.job?.title || 'Tracked job'}</h1><p>{app.job?.company} · Job: {app.job?.status || 'Unknown'}</p>
        <ApplicationStatusBadge status={app.status} />
        <p className="application-muted">Created: {applicationDate(app.created_at)} · Updated: {applicationDate(app.updated_at)}</p>
        <Link href={`/jobs/${app.job_id}`} className="btn btn-secondary">View job</Link>
      </section>
      <section className="card application-section"><h2>Application status</h2>
        <form onSubmit={e => { e.preventDefault(); void mutate('status'); }} className="application-actions">
          <label className="application-field">New status<select value={target} disabled={!!busy} onChange={e => setTarget(e.target.value as ApplicationStatus)}>
            <option value="">Choose next status</option>
            {APPLICATION_TRANSITIONS[app.status].map(s => <option value={s} key={s}>{statusLabel(s)}</option>)}
          </select></label>
          <Button type="submit" disabled={!!busy || !target} isLoading={busy === 'status'}>Update status</Button>
        </form>
      </section>
      <section className="card application-section"><h2>Private notes</h2>
        {notesSaved && <Alert variant="info">Notes saved</Alert>}
        <form onSubmit={e => { e.preventDefault(); void mutate('notes'); }}>
          <label className="application-field">Notes<textarea value={notes} maxLength={5000} rows={6} disabled={!!busy} onChange={e => setNotes(e.target.value)} /></label>
          <p className="application-muted">{notes.length}/5000 characters. Empty notes clear the saved text.</p>
          <Button type="submit" disabled={!!busy || notes.length > 5000} isLoading={busy === 'notes'}>Save notes</Button>
        </form>
      </section>
      <section className="card application-section"><h2>Status history</h2>
        {app.status_history.length === 0 ? <p>No status changes yet.</p> : <ol className="application-history">{app.status_history.map(h => <li key={h.id}>
          <span>{statusLabel(h.from_status)} → {statusLabel(h.to_status)}</span><time dateTime={h.changed_at || undefined}>{applicationDate(h.changed_at)}</time>
        </li>)}</ol>}
      </section>
      <section className="card application-section application-removal"><h2>Remove tracking</h2>
        <p>Removes this application, its notes and status history. The job remains available.</p>
        {!confirm ? <Button variant="ghost" disabled={!!busy} onClick={() => setConfirm(true)}>Remove application</Button> : <div role="group" aria-label="Confirm removal">
          <p>Remove this tracked application permanently?</p><div className="application-actions">
            <Button disabled={!!busy} isLoading={busy === 'delete'} onClick={() => void mutate('delete')}>Confirm removal</Button>
            <Button variant="secondary" disabled={!!busy} onClick={() => setConfirm(false)}>Cancel</Button>
          </div></div>}
      </section>
    </>}
  </div>;
}
