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
    <div className="form-field">
      {label && (
        <label htmlFor={inputId} >
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
        <span id={errorId} role="alert" className="form-error">
          {error}
        </span>
      )}
    </div>
  );
};
