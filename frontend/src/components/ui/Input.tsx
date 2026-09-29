import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  id,
  className = '',
  ...props
}) => {
  const generatedId = React.useId();
  const inputId = id || (label ? `${label.toLowerCase().replace(/\s+/g, '-')}-${generatedId}` : generatedId);
  const errorId = error ? `${inputId}-error` : undefined;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', width: '100%' }}>
      {label && (
        <label htmlFor={inputId} style={{ fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-secondary)' }}>
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={`input ${className}`}
        style={error ? { borderColor: 'var(--danger-border)' } : undefined}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={errorId}
        {...props}
      />
      {error && (
        <span id={errorId} role="alert" style={{ fontSize: '0.75rem', color: 'var(--danger-text)' }}>
          {error}
        </span>
      )}
    </div>
  );
};
