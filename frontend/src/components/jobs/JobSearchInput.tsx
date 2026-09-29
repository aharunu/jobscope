'use client';

import React, { useState, useEffect } from 'react';

export interface JobSearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export const JobSearchInput: React.FC<JobSearchInputProps> = ({
  value,
  onChange,
  placeholder = 'Search by job title or company name...',
}) => {
  const [internalValue, setInternalValue] = useState(value);

  // Sync internal state when external prop changes
  useEffect(() => {
    setInternalValue(value);
  }, [value]);

  // Debounce user keystrokes by 300ms
  useEffect(() => {
    const handler = setTimeout(() => {
      if (internalValue !== value) {
        onChange(internalValue);
      }
    }, 300);

    return () => clearTimeout(handler);
  }, [internalValue, value, onChange]);

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <div
        style={{
          position: 'absolute',
          left: '1rem',
          top: '50%',
          transform: 'translateY(-50%)',
          color: 'var(--text-muted)',
          display: 'flex',
          alignItems: 'center',
          pointerEvents: 'none',
        }}
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      </div>
      <input
        type="text"
        className="input"
        value={internalValue}
        onChange={(e) => setInternalValue(e.target.value)}
        placeholder={placeholder}
        style={{
          paddingLeft: '2.75rem',
          paddingRight: internalValue ? '2.5rem' : '1rem',
          height: '2.85rem',
          fontSize: '0.9375rem',
          borderRadius: 'var(--radius-md)',
        }}
        aria-label="Search jobs by title or company"
      />
      {internalValue && (
        <button
          type="button"
          onClick={() => {
            setInternalValue('');
            onChange('');
          }}
          aria-label="Clear search"
          style={{
            position: 'absolute',
            right: '0.85rem',
            top: '50%',
            transform: 'translateY(-50%)',
            color: 'var(--text-muted)',
            display: 'flex',
            alignItems: 'center',
            padding: '0.25rem',
            borderRadius: 'var(--radius-sm)',
          }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      )}
    </div>
  );
};
