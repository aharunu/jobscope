'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { createApplication, listApplications } from '@/lib/api/applications';
import { ApiError, type Application } from '@/lib/api/types';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { ApplicationStatusBadge } from './status';

export function ApplicationTrackingPanel({jobId}: {jobId: string}) {
  return <TrackingPanel key={jobId} jobId={jobId} />;
}
function TrackingPanel({jobId}: {jobId: string}) {
  const [app, setApp] = useState<Application | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const controllerRef = useRef<AbortController | null>(null);
  const locked = useRef(false);
  useEffect(() => {
    const controller = new AbortController(); controllerRef.current = controller;
    setLoading(true); setError('');
    listApplications({job_id: jobId, limit: 1}, controller.signal)
      .then(result => { if (!controller.signal.aborted) setApp(result.items[0] || null); })
      .catch(err => { if (!controller.signal.aborted) setError(err instanceof Error ? err.message : 'Unable to check application tracking.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [jobId, retry]);
  async function track() {
    const signal = controllerRef.current?.signal;
    if (locked.current || app || loading || error || !signal || signal.aborted) return;
    locked.current = true; setCreating(true); setError('');
    try {
      let result: Application;
      try { result = await createApplication(jobId, signal); }
      catch (err) {
        if (!(err instanceof ApiError) || err.code !== 'APPLICATION_ALREADY_EXISTS') throw err;
        const existing = await listApplications({job_id: jobId, limit: 1}, signal);
        if (!existing.items[0]) throw new Error('Tracking changed. Retry to check this job again.');
        result = existing.items[0];
      }
      if (!signal.aborted) setApp(result);
    } catch (err) { if (!signal.aborted) setError(err instanceof Error ? err.message : 'Unable to track application.'); }
    finally { locked.current = false; if (!signal.aborted) setCreating(false); }
  }
  return <section className="card application-section" aria-label="Application tracking">
    <h2>Application tracking</h2>
    <p>Track your progress independently of match scores or optional AI analysis.</p>
    {loading ? <p role="status">Checking tracking…</p> : app ? <>
      <p>Tracked · <ApplicationStatusBadge status={app.status} /></p>
      <Link href={`/applications/${app.id}`} className="btn btn-primary">Manage application</Link>
    </> : !error && <Button onClick={() => void track()} isLoading={creating}>Track Application</Button>}
    {error && <><Alert variant="danger">{error}</Alert><Button variant="secondary" disabled={creating} onClick={() => setRetry(v => v + 1)}>Retry tracking</Button></>}
  </section>;
}
