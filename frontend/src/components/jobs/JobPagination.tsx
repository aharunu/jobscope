'use client';

import React from 'react';
import { Button } from '../ui/Button';
import { Select } from '../ui/Select';
import { PAGE_SIZE_OPTIONS } from '../../lib/constants';

export interface JobPaginationProps {
  total: number;
  limit: number;
  offset: number;
  onPageChange: (newOffset: number) => void;
  onLimitChange: (newLimit: number) => void;
}

export const JobPagination: React.FC<JobPaginationProps> = ({
  total,
  limit,
  offset,
  onPageChange,
  onLimitChange,
}) => {
  const safeLimit = limit > 0 ? limit : 20;
  const safeOffset = Math.max(0, isNaN(offset) ? 0 : offset);
  const currentPage = Math.floor(safeOffset / safeLimit) + 1;
  const totalPages = Math.ceil(total / safeLimit) || 1;

  const startRecord = total === 0 ? 0 : Math.min(safeOffset + 1, total);
  const endRecord = Math.min(safeOffset + safeLimit, total);

  const canPrev = safeOffset > 0;
  const canNext = safeOffset + safeLimit < total;

  const handlePrev = () => {
    if (canPrev) {
      onPageChange(Math.max(0, safeOffset - safeLimit));
    }
  };

  const handleNext = () => {
    if (canNext) {
      onPageChange(safeOffset + safeLimit);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
        padding: '1.25rem 0',
        borderTop: '1px solid var(--border-subtle)',
        marginTop: '1.5rem',
      }}
    >
      {/* Range Display */}
      <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
        Showing <strong style={{ color: 'var(--text-primary)' }}>{startRecord}</strong>–
        <strong style={{ color: 'var(--text-primary)' }}>{endRecord}</strong> of{' '}
        <strong style={{ color: 'var(--text-primary)' }}>{total}</strong> jobs
      </div>

      {/* Pagination Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Per page:</span>
          <div style={{ width: '80px' }}>
            <Select
              options={PAGE_SIZE_OPTIONS.map((size) => ({
                value: String(size),
                label: String(size),
              }))}
              value={String(limit)}
              onChange={(e) => onLimitChange(Number(e.target.value))}
              style={{ padding: '0.35rem 0.5rem', fontSize: '0.8125rem' }}
              aria-label="Select number of jobs per page"
            />
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Button
            variant="secondary"
            onClick={handlePrev}
            disabled={!canPrev}
            style={{ padding: '0.45rem 0.85rem', fontSize: '0.8125rem' }}
            aria-label="Previous page"
          >
            ← Previous
          </Button>

          <span
            style={{
              fontSize: '0.8125rem',
              color: 'var(--text-secondary)',
              padding: '0 0.5rem',
            }}
          >
            Page {currentPage} of {totalPages}
          </span>

          <Button
            variant="secondary"
            onClick={handleNext}
            disabled={!canNext}
            style={{ padding: '0.45rem 0.85rem', fontSize: '0.8125rem' }}
            aria-label="Next page"
          >
            Next →
          </Button>
        </div>
      </div>
    </div>
  );
};
