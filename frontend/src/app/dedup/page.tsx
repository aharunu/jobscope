'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { dedupApi, DedupCandidate } from '@/lib/api/dedup';

export default function DedupPage() {
  const [items, setItems] = useState<DedupCandidate[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [confirmation, setConfirmation] = useState('');
  const submission = useRef(false);
  useEffect(() => {
    let mounted = true;
    setLoading(true); setError(''); setConfirmation('');
    dedupApi.list(offset).then(result => { if (mounted) { setItems(result.items); setTotal(result.total); } })
      .catch(err => { if (mounted) setError(err instanceof Error ? err.message : 'Unable to load review candidates'); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [offset]);
  async function resolve(id: string, merge: boolean) {
    if (submission.current) return;
    submission.current = true; setBusy(true); setError(''); setNotice('');
    try {
      const result = merge ? await dedupApi.merge(id) : await dedupApi.keepSeparate(id);
      setItems(old => old.filter(item => item.id !== id));
      setTotal(old => Math.max(0, old - 1)); setConfirmation('');
      setNotice(result.resolution === 'MERGED' ? 'Jobs merged. Saved matches require explicit recalculation.' : 'Jobs kept separate.');
      const refreshed = await dedupApi.list(offset);
      setItems(refreshed.items); setTotal(refreshed.total);
      if (!refreshed.items.length && offset > 0) setOffset(Math.max(0, offset - 25));
    } catch (err) { setError(err instanceof Error ? err.message : 'Review action failed. Please try again.'); }
    finally { submission.current = false; setBusy(false); }
  }
  return <div className="container" style={{ paddingTop: '2rem' }}>
    <h1>Duplicate review</h1>
    <p>Uncertain vacancies remain separate until reviewed. Compare evidence before merging.</p>
    {error && <Alert variant="danger">{error}</Alert>}
    {notice && <Alert>{notice}</Alert>}
    {loading ? <p>Loading candidates…</p> : !items.length && <p>No pending candidates.</p>}
    {items.map(item => <section key={item.id} className="card" style={{ padding: '1.5rem', marginBottom: '1rem' }} aria-label={`Candidate ${item.id}`}>
      <h2>{item.outcome} · Score {item.score} / 100</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.5rem' }}>
        {item.jobs.map(job => <article key={job.id}>
          <h3><Link href={`/jobs/${job.id}`}>{job.title}</Link></h3>
          <p>{job.company} · {job.location || 'Unknown location'}</p>
          <p>{job.employment_type || 'Unknown employment'} · {job.work_mode || 'Unknown work mode'}</p>
          <p>Published: {job.published_at ? new Date(job.published_at).toLocaleDateString() : 'Unknown'}</p>
          {job.sources.map((source, i) => <p key={i}>{source.source} · {source.ats_type} · {source.status}</p>)}
          <p style={{ whiteSpace: 'pre-wrap' }}>{job.description}</p>
        </article>)}
      </div>
      <details><summary>Signal explanation</summary><dl>{Object.entries(item.signals).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{String(value)}</dd></div>)}</dl></details>
      {confirmation === item.id ? <div>
        <Alert variant="warning">Confirm merging these vacancies? Applications and provenance are preserved. Conflicting applications block the merge. Historical matches will be invalidated.</Alert>
        <Button disabled={busy} onClick={() => resolve(item.id, true)}>Confirm merge</Button>{' '}
        <Button variant="secondary" disabled={busy} onClick={() => setConfirmation('')}>Cancel</Button>
      </div> : <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
        <Button disabled={busy || loading} onClick={() => setConfirmation(item.id)}>Merge</Button>
        <Button variant="secondary" disabled={busy || loading} onClick={() => resolve(item.id, false)}>Keep Separate</Button>
      </div>}
    </section>)}
    <div style={{ display: 'flex', gap: '1rem' }}>
      <Button disabled={busy || loading || !offset} onClick={() => setOffset(Math.max(0, offset - 25))}>Previous</Button>
      <span>{total} pending · Page {Math.floor(offset / 25) + 1}</span>
      <Button disabled={busy || loading || offset + 25 >= total} onClick={() => setOffset(offset + 25)}>Next</Button>
    </div>
  </div>;
}
