'use client';

import { WarningIcon } from '@/components/ui/icons';

import React from 'react';

export interface BlockerAlertProps {
  blockers: string[];
}

export const BlockerAlert: React.FC<BlockerAlertProps> = ({ blockers }) => {
  if (!blockers || blockers.length === 0) return null;

  return (
    <div className="alert-blocker" role="alert">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.875rem' }}>
        <WarningIcon size={18} aria-hidden="true" />
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
