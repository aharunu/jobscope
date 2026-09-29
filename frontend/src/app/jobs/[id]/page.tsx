import React, { Suspense } from 'react';
import { JobDetailClient } from './JobDetailClient';

interface JobDetailPageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ profile?: string }>;
}

export default async function JobDetailPage({ params, searchParams }: JobDetailPageProps) {
  const { id } = await params;
  const resolvedSearchParams = await searchParams;
  const initialProfileQuery = resolvedSearchParams?.profile;

  return (
    <Suspense
      fallback={
        <div className="container" style={{ paddingTop: '2rem' }}>
          <div style={{ color: 'var(--color-text-muted)', textAlign: 'center' }}>
            Loading job details...
          </div>
        </div>
      }
    >
      <JobDetailClient jobId={id} initialProfileQuery={initialProfileQuery} />
    </Suspense>
  );
}
