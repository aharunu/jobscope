'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import type { SearchProfileResponse, MatchResultResponse } from '@/lib/api/types';
import { evaluateMatch } from '@/lib/api/matching';
import { SearchProfileSelector } from '@/components/search_profile/SearchProfileSelector';
import { ScoreGauge } from '@/components/matching/ScoreGauge';
import { BlockerAlert } from '@/components/matching/BlockerAlert';
import { CategoryScoresBreakdown } from '@/components/matching/CategoryScoresBreakdown';
import { SkillsEvidenceList } from '@/components/matching/SkillsEvidenceList';
import { RequirementMatchesList } from '@/components/matching/RequirementMatchesList';
import { Alert } from '@/components/ui/Alert';

interface MatchPanelProps {
  jobId: string;
  searchProfiles: SearchProfileResponse[];
  selectedProfileId: string;
  onSelectProfile: (profileId: string) => void;
  initialMatchResult?: MatchResultResponse | null;
}

export function MatchPanel({
  jobId,
  searchProfiles,
  selectedProfileId,
  onSelectProfile,
  initialMatchResult = null,
}: MatchPanelProps) {
  // In-memory presentation cache (profileId -> MatchResultResponse)
  const [matchCache, setMatchCache] = useState<Record<string, MatchResultResponse>>(() => {
    if (initialMatchResult && selectedProfileId) {
      return { [selectedProfileId]: initialMatchResult };
    }
    return {};
  });

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const activeAbortControllerRef = useRef<AbortController | null>(null);

  // Strict profile isolation: currentMatch is derived strictly from selectedProfileId
  const currentMatch = selectedProfileId ? matchCache[selectedProfileId] ?? null : null;

  const performEvaluation = useCallback(
    async (profileId: string, bypassCache = false) => {
      if (!profileId || !jobId) return;

      if (!bypassCache && matchCache[profileId]) {
        // Already cached in memory for this exact profile
        return;
      }

      if (activeAbortControllerRef.current) {
        activeAbortControllerRef.current.abort();
      }
      const controller = new AbortController();
      activeAbortControllerRef.current = controller;

      setLoading(true);
      setError(null);
      setErrorStatus(null);

      try {
        const result = await evaluateMatch(
          {
            job_id: jobId,
            search_profile_id: profileId,
          },
          controller.signal
        );

        // Verify result matches expected profile & job before updating cache
        if (result && result.search_profile_id === profileId && result.job_id === jobId) {
          setMatchCache((prev) => ({
            ...prev,
            [profileId]: result,
          }));
        }
      } catch (err: unknown) {
        if ((err instanceof Error || err instanceof DOMException) && err.name === 'AbortError') {
          return;
        }

        let status = 500;
        let message = 'Failed to evaluate match against profile.';

        if (err instanceof Error) {
          message = err.message;
          if ('status' in err && typeof (err as { status: unknown }).status === 'number') {
            status = (err as { status: number }).status;
          }
        }

        setErrorStatus(status);
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    [jobId, matchCache]
  );

  useEffect(() => {
    if (selectedProfileId && !matchCache[selectedProfileId]) {
      performEvaluation(selectedProfileId, false);
    }
    return () => {
      if (activeAbortControllerRef.current) {
        activeAbortControllerRef.current.abort();
      }
    };
  }, [selectedProfileId, matchCache, performEvaluation]);

  const getErrorTitle = (status: number | null): string => {
    if (status === 401) return 'Authentication Required';
    if (status === 404) return 'Resource Not Found';
    if (status === 422) return 'Invalid Match Evaluation Request';
    return 'Match Evaluation Error';
  };

  const getErrorMessage = (status: number | null, fallbackMsg: string | null): string => {
    if (status === 401) return 'Authentication is required to perform match evaluation.';
    if (status === 404) return 'The specified job or candidate profile was not found.';
    if (status === 422) return 'The match parameters or profile configuration are invalid.';
    return fallbackMsg || 'An error occurred while evaluating the match.';
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--color-surface)',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--color-border)',
        padding: '1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
      }}
      data-testid="match-panel"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h2 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
              Deterministic Match Evaluation
            </h2>
            <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>
              Deterministic score engine evaluates your profile fit against job requirements.
            </p>
          </div>

          {selectedProfileId && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => performEvaluation(selectedProfileId, true)}
              disabled={loading}
              data-testid="re-evaluate-btn"
              style={{ fontSize: '0.8125rem', padding: '0.4rem 0.8rem' }}
            >
              {loading ? 'Evaluating...' : '↻ Re-evaluate'}
            </button>
          )}
        </div>

        <SearchProfileSelector
          profiles={searchProfiles}
          selectedProfileId={selectedProfileId}
          onSelectProfile={onSelectProfile}
          disabled={loading}
          jobId={jobId}
        />
      </div>

      {error && (
        <div data-testid="match-error-container" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <Alert variant="danger" title={getErrorTitle(errorStatus)}>
            {getErrorMessage(errorStatus, error)}
          </Alert>
          {selectedProfileId && (
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => performEvaluation(selectedProfileId, true)}
                disabled={loading}
                style={{ fontSize: '0.8125rem', padding: '0.35rem 0.75rem' }}
              >
                Retry Match Evaluation
              </button>
            </div>
          )}
        </div>
      )}

      {loading && !currentMatch && (
        <div
          style={{
            padding: '3rem 1rem',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem',
            color: 'var(--color-text-muted)',
          }}
          data-testid="match-loading"
          role="status"
          aria-live="polite"
        >
          <div
            style={{
              width: '2.5rem',
              height: '2.5rem',
              borderRadius: '50%',
              border: '3px solid var(--color-border)',
              borderTopColor: 'var(--color-primary)',
              animation: 'spin 1s linear infinite',
            }}
          />
          <p style={{ fontSize: '0.875rem' }}>Evaluating candidate profile against deterministic criteria...</p>
        </div>
      )}

      {!loading && !currentMatch && !error && searchProfiles.length === 0 && (
        <div
          style={{
            color: 'var(--color-text-muted)',
            fontSize: '0.875rem',
            padding: '1.25rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
            alignItems: 'flex-start',
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            borderRadius: 'var(--radius-md)',
            border: '1px dashed var(--color-border)',
          }}
          role="status"
          data-testid="match-panel-empty-profiles"
        >
          <p>No candidate search profiles found. Create a profile to evaluate match suitability.</p>
          <Link
            href={`/search-profiles/new?returnUrl=/jobs/${encodeURIComponent(jobId)}`}
            className="btn btn-secondary"
            style={{
              textDecoration: 'none',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.8125rem',
            }}
            data-testid="match-empty-create-profile-btn"
          >
            Create Search Profile
          </Link>
        </div>
      )}

      {currentMatch && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <ScoreGauge
            overallScore={currentMatch.overall_score}
            confidence={currentMatch.confidence}
          />

          {currentMatch.explanation?.blockers && currentMatch.explanation.blockers.length > 0 && (
            <BlockerAlert blockers={currentMatch.explanation.blockers} />
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
              Category Match Scores
            </h3>
            <CategoryScoresBreakdown categoryScores={currentMatch.category_scores} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
              Skills Evidence
            </h3>
            <SkillsEvidenceList explanation={currentMatch.explanation} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
              Requirement Matches & Evidence
            </h3>
            <RequirementMatchesList requirements={currentMatch.requirement_matches} />
          </div>
        </div>
      )}
    </div>
  );
}
