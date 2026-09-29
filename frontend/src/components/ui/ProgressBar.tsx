import React from 'react';

export interface ProgressBarProps {
  value: number; // 0 to 100
  max?: number;
  label?: string;
  showPercentage?: boolean;
  className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  label,
  showPercentage = true,
  className = '',
}) => {
  const percentage = Math.max(0, Math.min(100, Math.round((value / max) * 100)));

  const getVariantClass = (pct: number) => {
    if (pct >= 80) return 'progress-bar-high';
    if (pct >= 60) return 'progress-bar-mid';
    return 'progress-bar-low';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', width: '100%' }} className={className}>
      {(label || showPercentage) && (
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem' }}>
          {label && <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{label}</span>}
          {showPercentage && <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{percentage}%</span>}
        </div>
      )}
      <div
        className="progress-bar-container"
        role="progressbar"
        aria-valuenow={percentage}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label || 'Progress'}
      >
        <div
          className={`progress-bar-fill ${getVariantClass(percentage)}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};
