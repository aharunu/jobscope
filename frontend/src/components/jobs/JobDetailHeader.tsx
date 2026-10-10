'use client';

import { ArrowUpRightIcon, MapPinIcon } from '@/components/ui/icons';

import React from 'react';
import { JobDetailResponse } from '../../lib/api/types';
import { Badge } from '../ui/Badge';
import { formatRelativeTime, formatSalary, formatDate } from '../../lib/formatters';

export interface JobDetailHeaderProps {
  job: JobDetailResponse;
}

export const JobDetailHeader: React.FC<JobDetailHeaderProps> = ({ job }) => {
  const getWorkModeVariant = (mode?: string | null) => {
    if (!mode) return 'default';
    const lower = mode.toLowerCase();
    if (lower.includes('remote')) return 'remote';
    if (lower.includes('hybrid')) return 'hybrid';
    if (lower.includes('on-site') || lower.includes('onsite')) return 'onsite';
    return 'default';
  };

  return (
    <div
      className="card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem',
      }}
    >
      {/* Top Metadata: Company & Status */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
        }}
      >
        <span
          style={{
            fontSize: '1rem',
            fontWeight: 700,
            color: 'var(--primary-light)',
            textTransform: 'none',
            letterSpacing: '0.04em',
          }}
        >
          {job.company}
        </span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {job.status === 'ACTIVE' ? (
            <Badge variant="active">Active</Badge>
          ) : (
            <Badge variant="closed">Closed</Badge>
          )}
          {job.published_at && (
            <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
              Posted {formatDate(job.published_at)}
            </span>
          )}
        </div>
      </div>

      {/* Main Title & Action Row */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <h1
          style={{
            fontSize: '1.75rem',
            fontWeight: 650,
            lineHeight: 1.25,
            color: 'var(--text-primary)',
            letterSpacing: '-0.02em',
            maxWidth: '720px',
            wordBreak: 'break-word',
            overflowWrap: 'break-word',
          }}
        >
          {job.title}
        </h1>

        {job.canonical_url ? (
          <a
            href={job.canonical_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
            style={{
              padding: '0.75rem 1.5rem',
              fontSize: '0.9375rem',
              gap: '0.5rem',
            }}
            aria-label={`Apply on company website for ${job.title} at ${job.company}`}
          >
            <span>Apply on Company Site</span>
            <ArrowUpRightIcon size={15} aria-hidden="true" />
          </a>
        ) : (
          <button
            type="button"
            className="btn btn-secondary"
            disabled
            style={{
              padding: '0.75rem 1.25rem',
              fontSize: '0.875rem',
              opacity: 0.6,
              cursor: 'not-allowed',
            }}
          >
            Apply link unavailable
          </button>
        )}
      </div>

      {/* Tags Strip */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
        {job.location && (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.35rem',
              fontSize: '0.875rem',
              color: 'var(--text-secondary)',
              marginRight: '0.5rem',
              minWidth: 0,
              overflowWrap: 'anywhere',
            }}
          >
            <MapPinIcon size={15} style={{flexShrink: 0}} aria-hidden="true" />
            <span>{job.location}</span>
          </span>
        )}

        {job.work_mode && (
          <Badge variant={getWorkModeVariant(job.work_mode)}>{job.work_mode}</Badge>
        )}

        {job.employment_type && (
          <Badge variant="default">{job.employment_type}</Badge>
        )}

        {job.ats_type && (
          <Badge variant="source">{job.source_name || job.ats_type}</Badge>
        )}

        <div style={{ marginLeft: 'auto', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          <span style={{ color: 'var(--text-muted)' }}>Compensation: </span>
          <strong style={{ color: 'var(--text-primary)' }}>{formatSalary(job.salary)}</strong>
        </div>
      </div>
    </div>
  );
};
