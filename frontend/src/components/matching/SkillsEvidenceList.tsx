'use client';

import React from 'react';
import type { MatchExplanationResponse } from '@/lib/api/types';

interface SkillsEvidenceListProps {
  explanation: MatchExplanationResponse | null;
}

export function SkillsEvidenceList({ explanation }: SkillsEvidenceListProps) {
  if (!explanation) {
    return (
      <div style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
        No skill evidence available.
      </div>
    );
  }

  const { matched_skills = [], partial_matches = [], missing_skills = [] } = explanation;
  const hasSkills = matched_skills.length > 0 || partial_matches.length > 0 || missing_skills.length > 0;

  if (!hasSkills) {
    return (
      <div style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
        No specific skill requirements extracted for this position.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }} data-testid="skills-evidence-list">
      {matched_skills.length > 0 && (
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
            Matched Skills ({matched_skills.length})
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {matched_skills.map((skill, index) => (
              <span key={`matched-${skill}-${index}`} className="chip chip-matched">
                ✓ {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {partial_matches.length > 0 && (
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
            Partial Matches ({partial_matches.length})
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {partial_matches.map((skill, index) => (
              <span key={`partial-${skill}-${index}`} className="chip chip-partial">
                ~ {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {missing_skills.length > 0 && (
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
            Missing Skills ({missing_skills.length})
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {missing_skills.map((skill, index) => (
              <span key={`missing-${skill}-${index}`} className="chip chip-missing">
                ✕ {skill}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
