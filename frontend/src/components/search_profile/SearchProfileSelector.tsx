'use client';

import React from 'react';
import Link from 'next/link';
import { SearchProfileResponse } from '../../lib/api/types';
import { Select } from '../ui/Select';
import { Alert } from '../ui/Alert';

export interface SearchProfileSelectorProps {
  profiles: SearchProfileResponse[];
  selectedProfileId: string | null;
  onSelectProfile: (profileId: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
  jobId?: string;
  createProfileHref?: string;
}

export const SearchProfileSelector: React.FC<SearchProfileSelectorProps> = ({
  profiles,
  selectedProfileId,
  onSelectProfile,
  isLoading = false,
  disabled = false,
  jobId,
  createProfileHref,
}) => {
  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
        <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
          Search Profile
        </span>
        <div className="skeleton" style={{ height: '2.5rem', width: '100%', borderRadius: 'var(--radius-md)' }} />
      </div>
    );
  }

  if (profiles.length === 0) {
    const targetUrl =
      createProfileHref ||
      (jobId ? `/search-profiles/new?returnUrl=/jobs/${encodeURIComponent(jobId)}` : '/search-profiles/new');

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <Select
          label="Active Search Profile"
          options={[{ value: '', label: 'No search profiles available' }]}
          value=""
          disabled={true}
          data-testid="search-profile-selector"
          aria-label="Select candidate search profile for matching"
        />
        <Alert variant="warning" title="No Search Profiles">
          Matching requires at least one candidate Search Profile. Configure a profile to run evaluations.
        </Alert>
        <div>
          <Link
            href={targetUrl}
            className="btn btn-primary"
            style={{
              textDecoration: 'none',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.875rem',
            }}
            data-testid="create-search-profile-btn"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Create Search Profile
          </Link>
        </div>
      </div>
    );
  }

  const options = profiles.map((p) => ({
    value: p.id,
    label: p.name + (p.seniority ? ` (${p.seniority})` : ''),
  }));

  return (
    <Select
      label="Active Search Profile"
      options={options}
      value={selectedProfileId || profiles[0].id}
      onChange={(e) => onSelectProfile(e.target.value)}
      disabled={disabled}
      data-testid="search-profile-selector"
      aria-label="Select candidate search profile for matching"
    />
  );
};
