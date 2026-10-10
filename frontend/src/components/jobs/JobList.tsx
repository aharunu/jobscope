'use client';

import React from 'react';
import { JobSummaryResponse } from '../../lib/api/types';
import { JobCard } from './JobCard';
import { Button } from '../ui/Button';
import { MagnifyingGlassIcon, WarningCircleIcon } from '../ui/icons';

export interface JobListProps {
  jobs: JobSummaryResponse[];
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  hasActiveFilters: boolean;
  onResetFilters: () => void;
}

export const JobList: React.FC<JobListProps> = ({ jobs, isLoading, error, onRetry, hasActiveFilters, onResetFilters }) => {
  if (error) return <div className="empty-state" role="alert">
    <div className="empty-state-icon"><WarningCircleIcon size={24} aria-hidden="true" /></div>
    <h3>Failed to load jobs</h3><p>{error}</p><Button variant="secondary" onClick={onRetry}>Try Again</Button>
  </div>;
  if (isLoading) return <div className="jobs-grid" aria-busy="true" aria-label="Loading job postings">
    {Array.from({ length: 6 }, (_, index) => <div key={index} className="card" style={{ display: 'flex', gap: '1rem', minHeight: '150px' }}>
      <div className="skeleton" style={{ width: '44px', height: '44px', flexShrink: 0 }} />
      <div style={{ flex: 1, display: 'grid', gap: '.75rem', alignContent: 'start' }}>
        <div className="skeleton" style={{ width: '25%', height: '14px' }} />
        <div className="skeleton" style={{ width: '65%', height: '20px' }} />
        <div className="skeleton" style={{ width: '50%', height: '14px' }} />
      </div>
    </div>)}
  </div>;
  if (!jobs.length) return <div className="empty-state">
    <div className="empty-state-icon"><MagnifyingGlassIcon size={24} aria-hidden="true" /></div>
    <h3>{hasActiveFilters ? 'No jobs match your filters' : 'No jobs discovered yet'}</h3>
    <p>{hasActiveFilters ? 'Try adjusting your search query, switching work modes, or clearing your active filters.' : 'Preview and persist sources in Ingestion to add job postings.'}</p>
    {hasActiveFilters && <Button variant="secondary" onClick={onResetFilters}>Reset All Filters</Button>}
  </div>;
  return <div className="jobs-grid">{jobs.map(job => <JobCard key={job.id} job={job} />)}</div>;
};
