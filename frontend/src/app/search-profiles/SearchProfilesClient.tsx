'use client';

import { PlusIcon, UserCircleIcon, MapPinIcon, CurrencyDollarIcon, TrashIcon } from '@/components/ui/icons';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { listSearchProfiles, deleteSearchProfile } from '@/lib/api/search_profiles';
import type { SearchProfileResponse } from '@/lib/api/types';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Alert } from '@/components/ui/Alert';
import { CreateSearchProfileClient } from './new/CreateSearchProfileClient';

function formatSalaryRange(min: number | null, max: number | null): string | null {
  if (min != null && max != null) {
    return `$${min.toLocaleString()} - $${max.toLocaleString()}`;
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
  const [editing, setEditing] = useState<SearchProfileResponse | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

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

  if (editing) return <CreateSearchProfileClient key={editing.id} initialProfile={editing}
    onCancel={() => setEditing(null)} onSaved={updated => {
      setProfiles(current => current.map(profile => profile.id === updated.id ? updated : profile));
      setEditing(null); setSuccess('Search profile updated.');
    }}/>;

  return (
    <div className="container" style={{ paddingTop: '2rem', paddingBottom: '3rem' }}>
      {success && <p role="status">{success}</p>}
      {/* Header section */}
      <header className="page-header">
        <div>
          <h1>Search Profiles</h1>
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
          <PlusIcon size={18} aria-hidden="true" />
          Create Search Profile
        </Link>
      </header>

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
            gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 340px), 1fr))',
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
              backgroundColor: 'var(--accent-soft)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--primary-light)',
            }}
          >
            <UserCircleIcon size={28} aria-hidden="true" />
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
            <PlusIcon size={16} aria-hidden="true" />
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
            gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 360px), 1fr))',
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
                              backgroundColor: 'var(--bg-subtle)',
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
                              backgroundColor: 'var(--accent-soft)',
                              color: 'var(--primary-light)',
                              border: '1px solid var(--mode-remote-border)',
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
                        <MapPinIcon size={14} aria-hidden="true" />
                        <span>{profile.locations.join(', ')}</span>
                      </div>
                    )}

                    {salaryText && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--status-active-text)' }}>
                        <CurrencyDollarIcon size={14} aria-hidden="true" />
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
                    <>
                    <button type="button" className="btn btn-secondary" disabled={deletingId !== null}
                      aria-label={`Edit ${profile.name}`} data-testid={`edit-profile-btn-${profile.id}`}
                      onClick={() => {setConfirmDeleteId(null); setSuccess(null); setEditing(profile);}}>Edit</button>
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
                      <TrashIcon size={14} aria-hidden="true" />
                      Delete
                    </button>
                    </>
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
