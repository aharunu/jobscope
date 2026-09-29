'use client';

import React from 'react';
import type { RequirementMatchResponse, MatchStatus } from '@/lib/api/types';

interface RequirementMatchesListProps {
  requirements: RequirementMatchResponse[];
}

function getStatusChipClass(status: MatchStatus): string {
  switch (status) {
    case 'MATCHED':
      return 'chip chip-matched';
    case 'PARTIAL':
      return 'chip chip-partial';
    case 'NOT_MATCHED':
      return 'chip chip-missing';
    case 'UNKNOWN':
    default:
      return 'chip chip-partial';
  }
}

function getStatusLabel(status: MatchStatus): string {
  switch (status) {
    case 'MATCHED':
      return 'Matched';
    case 'PARTIAL':
      return 'Partial';
    case 'NOT_MATCHED':
      return 'Not Matched';
    case 'UNKNOWN':
    default:
      return 'Unknown';
  }
}

export function RequirementMatchesList({ requirements }: RequirementMatchesListProps) {
  if (!requirements || requirements.length === 0) {
    return (
      <div style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
        No requirement match breakdowns available.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }} data-testid="requirement-matches-list">
      {requirements.map((req) => {
        const percentage = Math.round(req.score * 100);

        return (
          <div
            key={req.id || req.requirement_id}
            style={{
              padding: '0.875rem 1rem',
              backgroundColor: 'var(--color-surface-hover)',
              borderRadius: 'var(--radius-md)',
              border: req.is_blocker && req.match_status === 'NOT_MATCHED' 
                ? '1px solid rgba(239, 68, 68, 0.4)' 
                : '1px solid var(--color-border)',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem',
            }}
            data-testid={`requirement-match-${req.requirement_id}`}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                <span className={getStatusChipClass(req.match_status)}>
                  {getStatusLabel(req.match_status)}
                </span>
                {req.is_blocker && (
                  <span
                    style={{
                      fontSize: '0.6875rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      padding: '0.15rem 0.45rem',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: 'rgba(239, 68, 68, 0.2)',
                      color: 'var(--color-danger)',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                    }}
                  >
                    Mandatory Blocker
                  </span>
                )}
              </div>
              <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
                Match: {percentage}%
              </div>
            </div>

            {req.reason && (
              <div style={{ fontSize: '0.875rem', color: 'var(--color-text-primary)', lineHeight: 1.5 }}>
                {req.reason}
              </div>
            )}

            {req.evidence && (
              <div
                style={{
                  fontSize: '0.8125rem',
                  color: 'var(--color-text-secondary)',
                  backgroundColor: 'var(--color-surface)',
                  padding: '0.5rem 0.75rem',
                  borderRadius: 'var(--radius-sm)',
                  borderLeft: '3px solid var(--color-primary)',
                  marginTop: '0.25rem',
                }}
              >
                <span style={{ fontWeight: 600, color: 'var(--color-text-muted)', marginRight: '0.35rem' }}>
                  Candidate Evidence:
                </span>
                {req.evidence}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
