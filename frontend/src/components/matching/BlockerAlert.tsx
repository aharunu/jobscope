'use client';

import React from 'react';

export interface BlockerAlertProps {
  blockers: string[];
}

export const BlockerAlert: React.FC<BlockerAlertProps> = ({ blockers }) => {
  if (!blockers || blockers.length === 0) return null;

  return (
    <div className="alert-blocker" role="alert">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.875rem' }}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <span>Hard Blocker Disqualification Detected</span>
      </div>
      <p style={{ fontSize: '0.8125rem', opacity: 0.9, lineHeight: 1.4 }}>
        The overall score was capped because the candidate does not meet the following mandatory requirement(s):
      </p>
      <ul style={{ margin: '0.25rem 0 0 1.25rem', fontSize: '0.8125rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
        {blockers.map((b, idx) => (
          <li key={idx} style={{ fontWeight: 500 }}>
            {b}
          </li>
        ))}
      </ul>
    </div>
  );
};
