'use client';

import { MagnifyingGlassIcon, XIcon } from '@/components/ui/icons';

import React, { useState, useEffect } from 'react';

export interface JobSearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  ariaLabel?: string;
}

export const JobSearchInput: React.FC<JobSearchInputProps> = ({
  value,
  onChange,
  placeholder = 'Search titles, companies and descriptions...',
  ariaLabel = 'Search jobs by title, company or description',
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
    <div>
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
          <MagnifyingGlassIcon size={18} aria-hidden="true" />
        </div>
        <input
          type="text"
          maxLength={200}
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
          aria-label={ariaLabel}
          aria-describedby="job-search-help"
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
            <XIcon size={16} aria-hidden="true" />
          </button>
        )}
      </div>
      <p id="job-search-help" className="job-search-help">
        Use double quotes for an exact word or phrase, e.g. &quot;intern&quot;.
      </p>
    </div>
  );
};
