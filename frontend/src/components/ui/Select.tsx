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
    <div className="form-field">
      {label && (
        <label htmlFor={selectId} >
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
        <span id={errorId} role="alert" className="form-error">
          {error}
        </span>
      )}
    </div>
  );
};
