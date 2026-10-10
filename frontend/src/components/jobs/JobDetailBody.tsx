'use client';

import React from 'react';
import { JobDetailResponse } from '../../lib/api/types';
import { Card } from '../ui/Card';
import { formatDate } from '../../lib/formatters';
import { parseJobContent, sanitizeJobHtml, hasHtmlTags } from '../../lib/jobContent';

export interface JobDetailBodyProps {
  job: JobDetailResponse;
}

export const JobDetailBody: React.FC<JobDetailBodyProps> = ({ job }) => {
  const content = parseJobContent(job.description, job.responsibilities);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Responsibilities Section */}
      {content.responsibilities && content.responsibilities.trim() && (
        <Card>
          <h2
            style={{
              fontSize: '1.1875rem',
              fontWeight: 700,
              color: 'var(--text-primary)',
              marginBottom: '0.75rem',
            }}
          >
            Responsibilities
          </h2>
          {hasHtmlTags(content.responsibilities) ? (
            <div
              className="job-content-html"
              dangerouslySetInnerHTML={{
                __html: sanitizeJobHtml(
                  content.responsibilities.includes('<li') &&
                    !content.responsibilities.includes('<ul')
                    ? `<ul>${content.responsibilities}</ul>`
                    : content.responsibilities
                ),
              }}
            />
          ) : (
            <div
              style={{
                color: 'var(--text-secondary)',
                lineHeight: 1.65,
                fontSize: '0.9375rem',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                overflowWrap: 'break-word',
              }}
            >
              {content.responsibilities}
            </div>
          )}
        </Card>
      )}

      {/* Structured Requirements Section (if extracted from structured job posting lists) */}
      {content.requirements && content.requirements.trim() && (
        <Card>
          <h2
            style={{
              fontSize: '1.1875rem',
              fontWeight: 700,
              color: 'var(--text-primary)',
              marginBottom: '0.75rem',
            }}
          >
            Requirements
          </h2>
          {hasHtmlTags(content.requirements) ? (
            <div
              className="job-content-html"
              dangerouslySetInnerHTML={{
                __html: sanitizeJobHtml(
                  content.requirements.includes('<li') &&
                    !content.requirements.includes('<ul')
                    ? `<ul>${content.requirements}</ul>`
                    : content.requirements
                ),
              }}
            />
          ) : (
            <div
              style={{
                color: 'var(--text-secondary)',
                lineHeight: 1.65,
                fontSize: '0.9375rem',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                overflowWrap: 'break-word',
              }}
            >
              {content.requirements}
            </div>
          )}
        </Card>
      )}

      {/* Description Section */}
      <Card>
        <h2
          style={{
            fontSize: '1.1875rem',
            fontWeight: 700,
            color: 'var(--text-primary)',
            marginBottom: '1rem',
          }}
        >
          Job Description
        </h2>
        {content.description && content.description.trim() ? (
          content.isHtml ? (
            <div
              className="job-content-html"
              dangerouslySetInnerHTML={{
                __html: sanitizeJobHtml(content.description),
              }}
            />
          ) : (
            <div
              style={{
                color: 'var(--text-secondary)',
                lineHeight: 1.7,
                fontSize: '0.9375rem',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                overflowWrap: 'break-word',
              }}
            >
              {content.description}
            </div>
          )
        ) : (
          <div
            style={{
              color: 'var(--text-secondary)',
              lineHeight: 1.7,
              fontSize: '0.9375rem',
            }}
          >
            No detailed description provided.
          </div>
        )}
      </Card>

      {/* Technical Metadata Footer */}
      <Card
        style={{
          backgroundColor: 'var(--bg-subtle)',
          borderStyle: 'dashed',
          padding: '1.25rem',
        }}
      >
        <h3
          style={{
            fontSize: '0.8125rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--text-muted)',
            marginBottom: '0.65rem',
          }}
        >
          Canonical Metadata
        </h3>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))',
            gap: '0.65rem',
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
          }}
        >
          <div>
            <span>Content Hash: </span>
            <code style={{ color: 'var(--primary-light)', wordBreak: 'break-all' }}>
              {job.content_hash.slice(0, 16)}...
            </code>
          </div>
          {job.external_job_id && (
            <div>
              <span>External ATS ID: </span>
              <strong style={{ color: 'var(--text-secondary)' }}>{job.external_job_id}</strong>
            </div>
          )}
          <div>
            <span>First Discovered: </span>
            <span style={{ color: 'var(--text-secondary)' }}>{formatDate(job.first_seen_at)}</span>
          </div>
          <div>
            <span>Last Verified: </span>
            <span style={{ color: 'var(--text-secondary)' }}>{formatDate(job.last_seen_at)}</span>
          </div>
        </div>
      </Card>
    </div>
  );
};
