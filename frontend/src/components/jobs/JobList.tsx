'use client';

import React from 'react';
import { JobSummaryResponse } from '../../lib/api/types';
import { JobCard } from './JobCard';
import { Button } from '../ui/Button';

export interface JobListProps {
  jobs: JobSummaryResponse[];
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  hasActiveFilters: boolean;
  onResetFilters: () => void;
}

export const JobList: React.FC<JobListProps> = ({
  jobs,
  isLoading,
  error,
  onRetry,
  hasActiveFilters,
  onResetFilters,
}) => {
  // 1. Error State
  if (error) {
    return (
      <div
        className="card"
        style={{
          padding: '2.5rem',
          textAlign: 'center',
          borderColor: 'var(--danger-border)',
          backgroundColor: 'rgba(239, 68, 68, 0.05)',
        }}
      >
        <div style={{ color: 'var(--danger-text)', marginBottom: '0.75rem', fontSize: '1.125rem', fontWeight: 600 }}>
          Failed to load jobs
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.25rem' }}>
          {error}
        </p>
        <Button variant="secondary" onClick={onRetry}>
          Try Again
        </Button>
      </div>
    );
  }

  // 2. Loading Skeletons
  if (isLoading) {
    return (
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
          gap: '1.25rem',
        }}
        aria-busy="true"
        aria-label="Loading job postings"
      >
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="card"
            style={{
              padding: '1.5rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
              minHeight: '190px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div className="skeleton" style={{ width: '35%', height: '1rem' }} />
              <div className="skeleton" style={{ width: '20%', height: '1.25rem', borderRadius: 'var(--radius-full)' }} />
            </div>
            <div className="skeleton" style={{ width: '75%', height: '1.5rem', margin: '0.25rem 0' }} />
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <div className="skeleton" style={{ width: '25%', height: '1.25rem', borderRadius: 'var(--radius-full)' }} />
              <div className="skeleton" style={{ width: '20%', height: '1.25rem', borderRadius: 'var(--radius-full)' }} />
            </div>
            <div
              style={{
                marginTop: 'auto',
                borderTop: '1px solid var(--border-subtle)',
                paddingTop: '0.75rem',
                display: 'flex',
                justifyContent: 'space-between',
              }}
            >
              <div className="skeleton" style={{ width: '30%', height: '0.875rem' }} />
              <div className="skeleton" style={{ width: '15%', height: '0.875rem' }} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  // 3. Empty State
  if (jobs.length === 0) {
    return (
      <div
        className="card"
        style={{
          padding: '3.5rem 1.5rem',
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '1rem',
        }}
      >
        <div
          style={{
            width: '3.5rem',
            height: '3.5rem',
            borderRadius: '50%',
            background: 'rgba(255, 255, 255, 0.05)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--text-muted)',
            marginBottom: '0.25rem',
          }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </div>

        <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
          {hasActiveFilters ? 'No jobs match your filters' : 'No jobs discovered yet'}
        </h3>

        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', maxWidth: '420px' }}>
          {hasActiveFilters
            ? 'Try adjusting your search query, switching work modes, or clearing your active filters.'
            : 'Active crawlers have not ingested any canonical job postings into the system yet.'}
        </p>

        {hasActiveFilters && (
          <Button variant="secondary" onClick={onResetFilters} style={{ marginTop: '0.5rem' }}>
            Reset All Filters
          </Button>
        )}
      </div>
    );
  }

  // 4. Populated Grid
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
        gap: '1.25rem',
      }}
    >
      {jobs.map((job) => (
        <JobCard key={job.id} job={job} />
      ))}
    </div>
  );
};
