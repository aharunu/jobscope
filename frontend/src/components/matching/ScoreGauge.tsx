'use client';

import React from 'react';

export interface ScoreGaugeProps {
  score?: number; // 0.00 to 100.00 verbatim from backend
  overallScore?: number; // alias for score
  confidence: number; // 0.00 to 100.00% verbatim from backend
}

export const ScoreGauge: React.FC<ScoreGaugeProps> = ({ score, overallScore, confidence }) => {
  const actualScore = score ?? overallScore ?? 0;
  const roundedScore = Math.round(actualScore);
  const roundedConfidence = Math.round(confidence);

  const getScoreColorClass = (val: number) => {
    if (val >= 80) return 'score-high';
    if (val >= 60) return 'score-mid';
    return 'score-low';
  };

  const getTierLabel = (val: number) => {
    if (val >= 80) return 'Strong Alignment';
    if (val >= 60) return 'Moderate Fit';
    return 'Low Alignment';
  };

  return (
    <div
      data-testid="score-gauge"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
        padding: '1.25rem',
        borderRadius: 'var(--radius-lg)',
        background: 'var(--bg-subtle)',
        border: '1px solid var(--border-subtle)',
      }}
    >
      <div>
        <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
          Overall Deterministic Match
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem', marginTop: '0.25rem' }}>
          <span
            className={getScoreColorClass(roundedScore)}
            style={{ fontSize: '2.5rem', fontWeight: 800, lineHeight: 1 }}
          >
            {roundedScore}
          </span>
          <span style={{ fontSize: '1rem', color: 'var(--text-muted)', fontWeight: 600 }}>/ 100</span>
        </div>
        <div style={{ fontSize: '0.8125rem', fontWeight: 600, marginTop: '0.35rem' }} className={getScoreColorClass(roundedScore)}>
          {getTierLabel(roundedScore)}
        </div>
      </div>

      <div style={{ textAlign: 'right' }}>
        <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
          Evidence Confidence
        </div>
        <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.25rem' }}>
          {roundedConfidence}%
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
          Deterministic Signals
        </div>
      </div>
    </div>
  );
};
