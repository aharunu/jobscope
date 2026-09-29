'use client';

import React from 'react';
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
  const hasActiveFilters = Boolean(
    filters.status ||
      filters.work_mode ||
      filters.employment_type ||
      filters.ats_type ||
      filters.company ||
      filters.location
  );

  return (
    <div
      className="card"
      style={{
        padding: '1.25rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span
          style={{
            fontSize: '0.875rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--text-secondary)',
          }}
        >
          Filters
        </span>
        {hasActiveFilters && (
          <Button
            variant="ghost"
            onClick={onReset}
            style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', color: 'var(--primary-light)' }}
          >
            Reset Filters
          </Button>
        )}
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '0.85rem',
        }}
      >
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
          options={ATS_TYPE_OPTIONS}
          value={filters.ats_type || ''}
          onChange={(e) => onChange({ ats_type: e.target.value || undefined })}
        />

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
