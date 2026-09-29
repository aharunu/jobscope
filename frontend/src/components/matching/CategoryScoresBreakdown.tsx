'use client';

import React from 'react';
import { ProgressBar } from '../ui/ProgressBar';

export interface CategoryScoresBreakdownProps {
  categoryScores: Record<string, number>;
}

const CATEGORY_LABELS: Record<string, string> = {
  ROLE: 'Role & Title Alignment',
  SKILLS: 'Technical & Required Skills',
  EXPERIENCE: 'Years of Experience & Seniority',
  LOCATION_WORK_MODE: 'Location & Work Mode Fit',
  EDUCATION: 'Education & Degree Level',
  OTHER: 'Industry & Additional Criteria',
};

export const CategoryScoresBreakdown: React.FC<CategoryScoresBreakdownProps> = ({
  categoryScores,
}) => {
  const entries = Object.entries(categoryScores);
  if (entries.length === 0) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
      <h3
        style={{
          fontSize: '0.875rem',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          color: 'var(--text-secondary)',
        }}
      >
        Category Evaluations
      </h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {entries.map(([catKey, rawScore]) => {
          const label = CATEGORY_LABELS[catKey] || catKey;
          // rawScore is on 0.0 - 1.0 normalized scale
          const percentage = Math.round(rawScore * 100);

          return (
            <ProgressBar
              key={catKey}
              label={label}
              value={percentage}
            />
          );
        })}
      </div>
    </div>
  );
};
