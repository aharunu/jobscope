'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { JobSummaryResponse } from '../../lib/api/types';
import { Badge } from '../ui/Badge';
import { Card } from '../ui/Card';
import { formatRelativeTime, formatSalary } from '../../lib/formatters';

export interface JobCardProps {
  job: JobSummaryResponse;
}

export const JobCard: React.FC<JobCardProps> = ({ job }) => {
  const router = useRouter();

  const handleCardClick = () => {
    router.push(`/jobs/${job.id}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      router.push(`/jobs/${job.id}`);
    }
  };

  const getWorkModeVariant = (mode?: string | null) => {
    if (!mode) return 'default';
    const lower = mode.toLowerCase();
    if (lower.includes('remote')) return 'remote';
    if (lower.includes('hybrid')) return 'hybrid';
    if (lower.includes('on-site') || lower.includes('onsite')) return 'onsite';
    return 'default';
  };

  return (
    <Card
      hoverable
      tabIndex={0}
      role="link"
      aria-label={`View details for ${job.title} at ${job.company}`}
      onClick={handleCardClick}
      onKeyDown={handleKeyDown}
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        cursor: 'pointer',
        gap: '1.25rem',
      }}
    >
      <div>
        {/* Top Metadata Bar: Company, Status, and Relative Date */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.75rem',
            marginBottom: '0.5rem',
          }}
        >
          <span
            style={{
              fontSize: '0.875rem',
              fontWeight: 600,
              color: 'var(--primary-light)',
              textTransform: 'uppercase',
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
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {formatRelativeTime(job.published_at || job.first_seen_at)}
            </span>
          </div>
        </div>

        {/* Job Title */}
        <h2
          style={{
            fontSize: '1.1875rem',
            fontWeight: 700,
            lineHeight: 1.35,
            color: 'var(--text-primary)',
            marginBottom: '0.75rem',
            wordBreak: 'break-word',
            overflowWrap: 'break-word',
          }}
        >
          {job.title}
        </h2>

        {/* Location & Tags Strip */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem', alignItems: 'center' }}>
          {job.location && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.25rem',
                fontSize: '0.8125rem',
                color: 'var(--text-secondary)',
                marginRight: '0.25rem',
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                <circle cx="12" cy="10" r="3" />
              </svg>
              {job.location}
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
        </div>
      </div>

      {/* Bottom Bar: Salary & Direct Apply Action */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderTop: '1px solid var(--border-subtle)',
          paddingTop: '0.85rem',
          marginTop: '0.25rem',
          flexWrap: 'wrap',
          gap: '0.5rem',
        }}
      >
        <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
          <span style={{ color: 'var(--text-muted)' }}>Comp: </span>
          <span style={{ fontWeight: 500 }}>{formatSalary(job.salary)}</span>
        </div>

        {job.canonical_url ? (
          <a
            href={job.canonical_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="btn btn-ghost"
            style={{
              padding: '0.35rem 0.65rem',
              fontSize: '0.75rem',
              gap: '0.25rem',
              borderRadius: 'var(--radius-sm)',
            }}
            aria-label={`Apply on company website for ${job.title} at ${job.company}`}
          >
            <span>Apply</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </a>
        ) : (
          <span
            style={{
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              fontStyle: 'italic',
            }}
          >
            Direct apply unavailable
          </span>
        )}
      </div>
    </Card>
  );
};
