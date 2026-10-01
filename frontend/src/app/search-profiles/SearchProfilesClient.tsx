'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { listSearchProfiles, deleteSearchProfile } from '@/lib/api/search_profiles';
import type { SearchProfileResponse } from '@/lib/api/types';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Alert } from '@/components/ui/Alert';

function formatSalaryRange(min: number | null, max: number | null): string | null {
  if (min != null && max != null) {
    return `$${min.toLocaleString()} – $${max.toLocaleString()}`;
  }
  if (min != null) {
    return `From $${min.toLocaleString()}`;
  }
  if (max != null) {
    return `Up to $${max.toLocaleString()}`;
  }
  return null;
}

export function SearchProfilesClient() {
  const [profiles, setProfiles] = useState<SearchProfileResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchProfiles = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const data = await listSearchProfiles(signal);
      setProfiles(data);
    } catch (err: unknown) {
      if ((err instanceof Error || err instanceof DOMException) && err.name === 'AbortError') return;
      const msg = err instanceof Error ? err.message : 'Failed to load search profiles.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchProfiles(controller.signal);
    return () => {
      controller.abort();
    };
  }, [fetchProfiles]);

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    setActionError(null);
    try {
      await deleteSearchProfile(id);
      setProfiles((prev) => prev.filter((p) => p.id !== id));
      setConfirmDeleteId(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete search profile.';
      setActionError(msg);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="container" style={{ paddingTop: '2rem', paddingBottom: '3rem' }}>
      {/* Header section */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '2rem',
        }}
      >
        <div>
          <h1
            style={{
              fontSize: '1.75rem',
              fontWeight: 700,
              color: 'var(--text-primary)',
              letterSpacing: '-0.02em',
            }}
          >
            Search Profiles
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            Manage candidate profiles used for deterministic job match evaluation.
          </p>
        </div>

        <Link
          href="/search-profiles/new"
          className="btn btn-primary"
          style={{
            textDecoration: 'none',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.625rem 1.25rem',
          }}
          data-testid="create-profile-header-btn"
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
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Create Search Profile
        </Link>
      </div>

      {/* Action / Global Error Alert */}
      {actionError && (
        <div style={{ marginBottom: '1.5rem' }}>
          <Alert variant="danger" title="Action Error">
            {actionError}
          </Alert>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div
          data-testid="profiles-loading"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
            gap: '1.25rem',
          }}
        >
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="skeleton"
              style={{
                height: '14rem',
                borderRadius: 'var(--radius-lg)',
                width: '100%',
              }}
            />
          ))}
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'flex-start' }}>
          <Alert variant="danger" title="Unable to Load Profiles">
            {error}
          </Alert>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => fetchProfiles()}
            data-testid="retry-fetch-profiles-btn"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && profiles.length === 0 && (
        <Card
          data-testid="empty-search-profiles"
          style={{
            padding: '3.5rem 2rem',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1.25rem',
            maxWidth: '600px',
            margin: '0 auto',
          }}
        >
          <div
            style={{
              width: '3.5rem',
              height: '3.5rem',
              borderRadius: '50%',
              backgroundColor: 'rgba(99, 102, 241, 0.12)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--primary-light)',
            }}
          >
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>
          <div>
            <h2
              style={{
                fontSize: '1.25rem',
                fontWeight: 600,
                color: 'var(--text-primary)',
                marginBottom: '0.5rem',
              }}
            >
              No search profiles yet
            </h2>
            <p
              style={{
                fontSize: '0.875rem',
                color: 'var(--text-secondary)',
                lineHeight: 1.5,
              }}
            >
              Search profiles store your target roles, skills, work modes, and compensation preferences
              to evaluate match suitability on Job Scope.
            </p>
          </div>

          <Link
            href="/search-profiles/new"
            className="btn btn-primary"
            style={{
              textDecoration: 'none',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              marginTop: '0.5rem',
            }}
            data-testid="create-profile-empty-btn"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Create Search Profile
          </Link>
        </Card>
      )}

      {/* Profiles list */}
      {!loading && !error && profiles.length > 0 && (
        <div
          data-testid="profiles-list"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
            gap: '1.5rem',
          }}
        >
          {profiles.map((profile) => {
            const salaryText = formatSalaryRange(profile.salary_min, profile.salary_max);
            const isConfirming = confirmDeleteId === profile.id;
            const isDeleting = deletingId === profile.id;

            return (
              <Card
                key={profile.id}
                data-testid={`profile-card-${profile.id}`}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  padding: '1.5rem',
                  gap: '1.25rem',
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {/* Title & Seniority Header */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      justifyContent: 'space-between',
                      gap: '0.75rem',
                    }}
                  >
                    <div>
                      <h2
                        style={{
                          fontSize: '1.125rem',
                          fontWeight: 600,
                          color: 'var(--text-primary)',
                        }}
                      >
                        {profile.name}
                      </h2>
                    </div>
                    {profile.seniority && (
                      <Badge variant="default" style={{ flexShrink: 0 }}>
                        {profile.seniority}
                      </Badge>
                    )}
                  </div>

                  {/* Target Roles */}
                  {profile.target_roles && profile.target_roles.length > 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Target Roles
                      </span>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
                        {profile.target_roles.map((role, idx) => (
                          <span
                            key={idx}
                            style={{
                              fontSize: '0.8125rem',
                              padding: '0.2rem 0.5rem',
                              borderRadius: 'var(--radius-sm)',
                              backgroundColor: 'rgba(255, 255, 255, 0.06)',
                              color: 'var(--text-primary)',
                            }}
                          >
                            {role}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Target Skills */}
                  {profile.target_skills && profile.target_skills.length > 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Target Skills
                      </span>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
                        {profile.target_skills.map((skill, idx) => (
                          <span
                            key={idx}
                            style={{
                              fontSize: '0.75rem',
                              padding: '0.15rem 0.45rem',
                              borderRadius: 'var(--radius-sm)',
                              backgroundColor: 'rgba(99, 102, 241, 0.12)',
                              color: 'var(--primary-light)',
                              border: '1px solid rgba(99, 102, 241, 0.2)',
                            }}
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Work Modes & Locations */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                    {profile.work_modes && profile.work_modes.length > 0 && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Work Modes:</span>
                        {profile.work_modes.map((wm, idx) => {
                          const lower = wm.toLowerCase();
                          const variant = lower.includes('remote') ? 'remote' : lower.includes('hybrid') ? 'hybrid' : lower.includes('onsite') || lower.includes('on-site') ? 'onsite' : 'default';
                          return (
                            <Badge key={idx} variant={variant}>
                              {wm}
                            </Badge>
                          );
                        })}
                      </div>
                    )}

                    {profile.locations && profile.locations.length > 0 && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--text-muted)' }}>
                          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                          <circle cx="12" cy="10" r="3" />
                        </svg>
                        <span>{profile.locations.join(', ')}</span>
                      </div>
                    )}

                    {salaryText && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--status-active-text)' }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <line x1="12" y1="1" x2="12" y2="23" />
                          <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                        </svg>
                        <span>{salaryText}</span>
                      </div>
                    )}

                    {profile.industries && profile.industries.length > 0 && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Industries:</span>
                        <span>{profile.industries.join(', ')}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Footer Actions */}
                <div
                  style={{
                    borderTop: '1px solid var(--border-subtle)',
                    paddingTop: '1rem',
                    display: 'flex',
                    justifyContent: 'flex-end',
                    alignItems: 'center',
                    gap: '0.75rem',
                  }}
                >
                  {isConfirming ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--danger-text)' }}>Delete?</span>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => setConfirmDeleteId(null)}
                        disabled={isDeleting}
                        style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(profile.id)}
                        disabled={isDeleting}
                        style={{
                          fontSize: '0.75rem',
                          padding: '0.3rem 0.6rem',
                          backgroundColor: 'var(--danger-bg)',
                          color: 'var(--danger-text)',
                          border: '1px solid var(--danger-border)',
                          borderRadius: 'var(--radius-sm)',
                          cursor: isDeleting ? 'not-allowed' : 'pointer',
                        }}
                        data-testid={`confirm-delete-${profile.id}`}
                      >
                        {isDeleting ? 'Deleting...' : 'Confirm'}
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setConfirmDeleteId(profile.id)}
                      className="btn btn-ghost"
                      style={{
                        fontSize: '0.8125rem',
                        color: 'var(--text-muted)',
                        padding: '0.35rem 0.7rem',
                      }}
                      data-testid={`delete-profile-btn-${profile.id}`}
                      aria-label={`Delete ${profile.name}`}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                      Delete
                    </button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
