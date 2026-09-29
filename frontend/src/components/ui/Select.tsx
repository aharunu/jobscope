import React from 'react';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: readonly SelectOption[] | SelectOption[];
  error?: string;
}

export const Select: React.FC<SelectProps> = ({
  label,
  options,
  error,
  id,
  className = '',
  ...props
}) => {
  const generatedId = React.useId();
  const selectId = id || (label ? `${label.toLowerCase().replace(/\s+/g, '-')}-${generatedId}` : generatedId);
  const errorId = error ? `${selectId}-error` : undefined;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', width: '100%' }}>
      {label && (
        <label htmlFor={selectId} style={{ fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-secondary)' }}>
          {label}
        </label>
      )}
      <select
        id={selectId}
        className={`select ${className}`}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={errorId}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && (
        <span id={errorId} role="alert" style={{ fontSize: '0.75rem', color: 'var(--danger-text)' }}>
          {error}
        </span>
      )}
    </div>
  );
};
