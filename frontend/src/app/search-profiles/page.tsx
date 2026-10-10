import React, { Suspense } from 'react';
import { SearchProfilesClient } from './SearchProfilesClient';

export const metadata = {
  title: 'Search Profiles - JobScope',
  description: 'Manage candidate search profiles and criteria for job matching.',
};

export default function SearchProfilesPage() {
  return (
    <Suspense
      fallback={
        <div className="container" style={{ paddingTop: '2rem' }}>
          <div style={{ color: 'var(--text-muted)', textAlign: 'center' }}>
            Loading search profiles...
          </div>
        </div>
      }
    >
      <SearchProfilesClient />
    </Suspense>
  );
}
