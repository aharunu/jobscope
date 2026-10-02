'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { listApplications } from '@/lib/api/applications';
import type { ApplicationListResponse, ApplicationStatus } from '@/lib/api/types';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { APPLICATION_STATUSES, ApplicationStatusBadge, applicationDate, statusLabel } from './status';

export function ApplicationsClient() {
  const [status, setStatus] = useState<ApplicationStatus | ''>('');
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<ApplicationListResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(''); setData(null);
    listApplications({status: status || undefined, limit: 20, offset}, controller.signal)
      .then(result => { if (!controller.signal.aborted) setData(result); })
      .catch(err => { if (!controller.signal.aborted) setError(err instanceof Error ? err.message : 'Unable to load applications.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [status, offset, retry]);
  return <div className="container application-page">
    <h1>Applications</h1>
    <p className="application-muted">Manage your tracked jobs, notes and application progress.</p>
    <label className="application-field">Filter by status
      <select value={status} onChange={e => { setStatus(e.target.value as ApplicationStatus | ''); setOffset(0); }}>
        <option value="">All statuses</option>
        {APPLICATION_STATUSES.map(s => <option key={s} value={s}>{statusLabel(s)}</option>)}
      </select>
    </label>
    {loading && <p role="status">Loading applications…</p>}
    {error && <><Alert variant="danger">{error}</Alert><Button onClick={() => setRetry(v => v + 1)}>Retry applications</Button></>}
    {!loading && data && <>
      {data.items.length === 0 ? <section className="card application-section">
        <h2>{status ? 'No applications with this status.' : 'No applications tracked yet.'}</h2>
        <p>Browse jobs and use “Track Application” to add one.</p>
        <Link href="/jobs" className="btn btn-primary">Browse jobs</Link>
      </section> : <>
        <p>{data.total} tracked {data.total === 1 ? 'application' : 'applications'}</p>
        <div className="application-grid">{data.items.map(app => <article key={app.id} className="card application-section">
          <ApplicationStatusBadge status={app.status} />
          <h2><Link href={`/applications/${app.id}`}>{app.job?.title || 'Tracked job'}</Link></h2>
          <p>{app.job?.company || 'Company not available'} · Job: {app.job?.status || 'Unknown'}</p>
          <p className="application-notes-preview">{app.notes || 'No notes yet.'}</p>
          <p className="application-muted">Created: {applicationDate(app.created_at)}<br />Updated: {applicationDate(app.updated_at)}</p>
          <div className="application-actions"><Link href={`/applications/${app.id}`} className="btn btn-primary">Manage application</Link>
            <Link href={`/jobs/${app.job_id}`} className="btn btn-secondary">View job</Link></div>
        </article>)}</div>
        <div className="application-actions" aria-label="Application pagination">
          <Button variant="secondary" disabled={offset === 0} onClick={() => setOffset(v => Math.max(0, v - 20))}>Previous</Button>
          <span>Page {Math.floor(offset / 20) + 1}</span>
          <Button variant="secondary" disabled={offset + data.items.length >= data.total} onClick={() => setOffset(v => v + 20)}>Next</Button>
        </div>
      </>}
    </>}
  </div>;
}
