import React from 'react';

export interface AlertProps {
  variant?: 'danger' | 'warning' | 'info';
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const Alert: React.FC<AlertProps> = ({
  variant = 'info',
  title,
  children,
  className = '',
}) => {
  const getStyles = () => {
    switch (variant) {
      case 'danger':
        return {
          background: 'var(--danger-bg)',
          borderColor: 'var(--danger-border)',
          color: 'var(--danger-text)',
        };
      case 'warning':
        return {
          background: 'rgba(245, 158, 11, 0.12)',
          borderColor: 'rgba(245, 158, 11, 0.3)',
          color: 'var(--mode-onsite-text)',
        };
      case 'info':
      default:
        return {
          background: 'rgba(99, 102, 241, 0.12)',
          borderColor: 'rgba(99, 102, 241, 0.3)',
          color: 'var(--primary-light)',
        };
    }
  };

  const style = getStyles();

  return (
    <div
      role="alert"
      className={className}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.35rem',
        padding: '0.875rem 1.25rem',
        borderRadius: 'var(--radius-md)',
        border: `1px solid ${style.borderColor}`,
        backgroundColor: style.background,
        color: style.color,
        fontSize: '0.875rem',
      }}
    >
      {title && <strong style={{ fontWeight: 600 }}>{title}</strong>}
      <div style={{ color: 'var(--text-primary)', opacity: 0.9 }}>{children}</div>
    </div>
  );
};
