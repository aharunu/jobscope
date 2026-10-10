'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { JobSummaryResponse } from '../../lib/api/types';
import { Badge } from '../ui/Badge';
import { Card } from '../ui/Card';
import { MapPinIcon, ArrowUpRightIcon } from '../ui/icons';
import { formatRelativeTime, formatSalary } from '../../lib/formatters';

export interface JobCardProps { job: JobSummaryResponse; }

export const JobCard: React.FC<JobCardProps> = ({ job }) => {
  const router = useRouter();
  const open = () => router.push(`/jobs/${job.id}`);
  const handleKeyDown = (event: React.KeyboardEvent) => {
    // Nested Apply links retain their own keyboard behavior.
    if (event.target !== event.currentTarget) return;
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); open(); }
  };
  const mode = job.work_mode?.toLowerCase() || '';
  const modeVariant = mode.includes('remote') ? 'remote' : mode.includes('hybrid') ? 'hybrid' : mode.includes('on-site') || mode.includes('onsite') ? 'onsite' : 'default';
  return <Card hoverable className="job-card" tabIndex={0} role="link"
    aria-label={`View details for ${job.title} at ${job.company}`} onClick={open} onKeyDown={handleKeyDown}>
    <div className="company-monogram" aria-hidden="true">{job.company?.trim().slice(0, 1).toLocaleUpperCase() || '?'}</div>
    <div className="job-card-copy">
      <div className="job-card-company">{job.company}</div>
      <h2 className="job-card-title">{job.title}</h2>
      {job.location && <div className="job-card-location"><MapPinIcon size={14} aria-hidden="true" /><span title={job.location}>{job.location}</span></div>}
      <div className="job-card-tags">
        {job.work_mode && <Badge variant={modeVariant}>{job.work_mode}</Badge>}
        {job.employment_type && <Badge>{job.employment_type}</Badge>}
        {job.ats_type && <Badge variant="source">{job.source_name || job.ats_type}</Badge>}
        <span className="job-card-salary">Comp: <span>{formatSalary(job.salary)}</span></span>
      </div>
    </div>
    <div className="job-card-side">
      <div className="job-card-meta"><Badge variant={job.status === 'ACTIVE' ? 'active' : 'closed'}>{job.status === 'ACTIVE' ? 'Active' : 'Closed'}</Badge>
        <span className="job-card-date">{formatRelativeTime(job.published_at || job.first_seen_at)}</span>
      </div>
      {job.canonical_url ? <a href={job.canonical_url} target="_blank" rel="noopener noreferrer" onClick={event => event.stopPropagation()}
        className="btn btn-ghost job-card-action" aria-label={`Apply on company website for ${job.title} at ${job.company}`}>
        Apply <ArrowUpRightIcon size={15} aria-hidden="true" />
      </a> : <span className="job-card-date">Direct apply unavailable</span>}
    </div>
  </Card>;
};
