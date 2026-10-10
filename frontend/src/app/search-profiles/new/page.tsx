import React, { Suspense } from 'react';
import { CreateSearchProfileClient } from './CreateSearchProfileClient';

export const metadata = {
  title: 'Create Search Profile - JobScope',
  description: 'Create a new candidate search profile for job matching evaluations.',
};

export default function CreateSearchProfilePage() {
  return (
    <Suspense
      fallback={
        <div className="container" style={{ paddingTop: '2rem' }}>
          <div style={{ color: 'var(--text-muted)', textAlign: 'center' }}>
            Loading search profile form...
          </div>
        </div>
      }
    >
      <CreateSearchProfileClient />
    </Suspense>
  );
}
