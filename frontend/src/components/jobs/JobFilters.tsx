'use client';

import { SlidersHorizontalIcon } from '../ui/icons';
import React, { useEffect, useState } from 'react';
import { listSourcePlatforms } from '../../lib/api/sources';
import { Select } from '../ui/Select';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import {
  WORK_MODE_OPTIONS,
  EMPLOYMENT_TYPE_OPTIONS,
  STATUS_OPTIONS,
  ATS_TYPE_OPTIONS,
} from '../../lib/constants';
import { JobFilterParams } from '../../lib/api/types';

export interface JobFiltersProps {
  filters: JobFilterParams;
  onChange: (updatedFilters: Partial<JobFilterParams>) => void;
  onReset: () => void;
}

export const JobFilters: React.FC<JobFiltersProps> = ({
  filters,
  onChange,
  onReset,
}) => {
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [platformError, setPlatformError] = useState(false);
  useEffect(() => {
    let controller: AbortController | undefined;
    let mounted = true;
    const refresh = async () => {
      controller?.abort();
      const request = new AbortController();
      controller = request;
      try {
        const values = await listSourcePlatforms(request.signal);
        if (mounted && !request.signal.aborted) { setPlatforms(values); setPlatformError(false); }
      } catch {
        if (mounted && !request.signal.aborted) setPlatformError(true);
      }
    };
    const visible = () => { if (document.visibilityState === 'visible') void refresh(); };
    void refresh();
    window.addEventListener('focus', refresh);
    document.addEventListener('visibilitychange', visible);
    return () => {
      mounted = false; controller?.abort();
      window.removeEventListener('focus', refresh);
      document.removeEventListener('visibilitychange', visible);
    };
  }, []);
  const platformOptions = [
    ...ATS_TYPE_OPTIONS,
    ...[...new Set([...platforms, filters.ats_type || ''])]
      .filter(value => value && !ATS_TYPE_OPTIONS.some(option => option.value === value))
      .sort().map(value => ({ value, label: value === 'kariyer_net' ? 'Kariyer.net' : value })),
  ];
  const hasActiveFilters = Boolean(
    filters.status ||
      filters.work_mode ||
      filters.employment_type ||
      filters.ats_type ||
      filters.company ||
      filters.location
  );

  return (
    <div className="card filters-panel">
      <div className="filters-heading">
        <span><SlidersHorizontalIcon size={16} aria-hidden="true" />Filters</span>
        {hasActiveFilters && <Button variant="ghost" onClick={onReset}>Reset Filters</Button>}
      </div>
      <div className="filters-grid">
        <Select
          label="Status"
          options={STATUS_OPTIONS}
          value={filters.status || ''}
          onChange={(e) => onChange({ status: e.target.value || undefined })}
        />

        <Select
          label="Work Mode"
          options={WORK_MODE_OPTIONS}
          value={filters.work_mode || ''}
          onChange={(e) => onChange({ work_mode: e.target.value || undefined })}
        />

        <Select
          label="Employment Type"
          options={EMPLOYMENT_TYPE_OPTIONS}
          value={filters.employment_type || ''}
          onChange={(e) => onChange({ employment_type: e.target.value || undefined })}
        />

        <Select
          label="Source Platform"
          options={platformOptions}
          value={filters.ats_type || ''}
          onChange={(e) => onChange({ ats_type: e.target.value || undefined })}
        />

        {platformError && <p role="status">Platform list could not be refreshed. Existing options remain available.</p>}

        <Input
          label="Company"
          placeholder="Filter by company..."
          value={filters.company || ''}
          onChange={(e) => onChange({ company: e.target.value || undefined })}
        />

        <Input
          label="Location"
          placeholder="Filter by location..."
          value={filters.location || ''}
          onChange={(e) => onChange({ location: e.target.value || undefined })}
        />
      </div>
    </div>
  );
};
