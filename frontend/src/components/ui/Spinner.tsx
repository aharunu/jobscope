import React from 'react';

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  className?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  label = 'Loading...',
  className = '',
}) => {
  const sizeMap = {
    sm: '1rem',
    md: '1.75rem',
    lg: '2.5rem',
  };

  return (
    <div
      role="status"
      aria-label={label}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.5rem',
      }}
      className={className}
    >
      <span
        style={{
          display: 'inline-block',
          width: sizeMap[size],
          height: sizeMap[size],
          border: '2px solid var(--border-card)',
          borderTopColor: 'var(--primary)',
          borderRadius: '50%',
          animation: 'spin 0.7s linear infinite',
        }}
      />
      <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{label}</span>
    </div>
  );
};
