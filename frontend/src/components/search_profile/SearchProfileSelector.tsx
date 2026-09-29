'use client';

import React from 'react';
import { SearchProfileResponse } from '../../lib/api/types';
import { Select } from '../ui/Select';
import { Alert } from '../ui/Alert';

export interface SearchProfileSelectorProps {
  profiles: SearchProfileResponse[];
  selectedProfileId: string | null;
  onSelectProfile: (profileId: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
}

export const SearchProfileSelector: React.FC<SearchProfileSelectorProps> = ({
  profiles,
  selectedProfileId,
  onSelectProfile,
  isLoading = false,
  disabled = false,
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
