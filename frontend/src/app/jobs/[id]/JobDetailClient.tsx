'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getJobById } from '@/lib/api/jobs';
import { listSearchProfiles } from '@/lib/api/search_profiles';
import type { JobDetailResponse, SearchProfileResponse } from '@/lib/api/types';
import { JobDetailHeader } from '@/components/jobs/JobDetailHeader';
import { JobDetailBody } from '@/components/jobs/JobDetailBody';
import { MatchPanel } from '@/components/matching/MatchPanel';
import { Alert } from '@/components/ui/Alert';
import { ApplicationTrackingPanel } from '@/components/applications/ApplicationTrackingPanel';

interface JobDetailClientProps {
  jobId: string;
  initialProfileQuery?: string;
}

export function JobDetailClient({ jobId, initialProfileQuery }: JobDetailClientProps) {
  const router = useRouter();

  const [job, setJob] = useState<JobDetailResponse | null>(null);
  const [searchProfiles, setSearchProfiles] = useState<SearchProfileResponse[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<string>('');

  const [loadingJob, setLoadingJob] = useState<boolean>(true);
  const [loadingProfiles, setLoadingProfiles] = useState<boolean>(true);
  const [jobError, setJobError] = useState<string | null>(null);
  const [jobStatusCode, setJobStatusCode] = useState<number | null>(null);
  const [profilesError, setProfilesError] = useState<string | null>(null);

  const activeAbortControllerRef = useRef<AbortController | null>(null);

  // Fetch Job details
  const fetchJob = useCallback(async (signal?: AbortSignal) => {
    signal = signal ?? activeAbortControllerRef.current?.signal;
    setLoadingJob(true);
    setJobError(null);
    setJobStatusCode(null);
    try {
      const data = await getJobById(jobId, signal);
      if (!signal?.aborted) setJob(data);
    } catch (err: unknown) {
      if (signal?.aborted) return;
      if ((err instanceof Error || err instanceof DOMException) && err.name === 'AbortError') return;
      if (err instanceof Error && 'status' in err) {
        setJobStatusCode((err as { status: number }).status);
      }
      const msg = err instanceof Error ? err.message : 'Failed to load job details.';
      setJobError(msg);
    } finally {
      if (!signal?.aborted) setLoadingJob(false);
    }
  }, [jobId]);

  // Fetch Candidate Search Profiles
  const fetchProfiles = useCallback(async (signal?: AbortSignal) => {
    setLoadingProfiles(true);
    setProfilesError(null);
    try {
      const profiles = await listSearchProfiles(signal);
      if (!signal?.aborted) setSearchProfiles(profiles);
    } catch (err: unknown) {
      if (signal?.aborted) return;
      if (err instanceof Error && err.name === 'AbortError') return;
      const msg = err instanceof Error ? err.message : 'Failed to load search profiles.';
      setProfilesError(msg);
    } finally {
      if (!signal?.aborted) setLoadingProfiles(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    activeAbortControllerRef.current = controller;

    fetchJob(controller.signal);
    fetchProfiles(controller.signal);

    return () => {
      controller.abort();
    };
  }, [fetchJob, fetchProfiles]);

  // Search Profile selection precedence:
  // 1. Valid URL ?profile=<id>
  // 2. Valid localStorage profile ID
  // 3. First returned profile
  useEffect(() => {
    if (searchProfiles.length === 0) {
      setSelectedProfileId('');
      return;
    }

    // 1. Check URL query
    const urlProfile =
      initialProfileQuery ||
      (typeof window !== 'undefined'
        ? new URLSearchParams(window.location.search).get('profile')
        : null);

    if (urlProfile && searchProfiles.some((p) => p.id === urlProfile)) {
      setSelectedProfileId(urlProfile);
      return;
    }

    // 2. Check localStorage on client safely
    if (typeof window !== 'undefined') {
      try {
        const storedId = localStorage.getItem('jobscope_selected_profile_id');
        if (storedId && searchProfiles.some((p) => p.id === storedId)) {
          setSelectedProfileId(storedId);
          return;
        }
      } catch {
        // Ignore localStorage access errors
      }
    }

    // 3. Default to first profile
    setSelectedProfileId(searchProfiles[0].id);
  }, [searchProfiles, initialProfileQuery]);

  const handleSelectProfile = (newId: string) => {
    setSelectedProfileId(newId);
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('jobscope_selected_profile_id', newId);
      } catch {
        // Ignore localStorage quota/permission errors
      }

      // Update URL query string without page refresh
      const currentUrl = new URL(window.location.href);
      currentUrl.searchParams.set('profile', newId);
      window.history.replaceState(null, '', currentUrl.toString());
    }
  };

  const handleBackToDiscovery = () => {
    let returnUrl = '/jobs';
    if (typeof window !== 'undefined') {
      try {
        const savedUrl = sessionStorage.getItem('jobscope_last_discovery_url');
        if (savedUrl) {
          returnUrl = savedUrl;
        }
      } catch {
        // Fallback to /jobs
      }
    }
    router.push(returnUrl);
  };

  return (
    <div className="container" style={{ paddingTop: '1.5rem', paddingBottom: '4rem' }}>
      {/* Back Navigation Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '1.5rem',
          flexWrap: 'wrap',
          gap: '0.75rem',
        }}
      >
        <button
          type="button"
          onClick={handleBackToDiscovery}
          className="btn btn-secondary"
          style={{ fontSize: '0.875rem', gap: '0.5rem' }}
          data-testid="back-to-discovery"
        >
          ← Back to Job Discovery
        </button>

        {job && (
          <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>
            <span>Jobs</span>
            <span style={{ margin: '0 0.5rem' }}>/</span>
            <span style={{ color: 'var(--color-text-secondary)', fontWeight: 500 }}>
              {job.title}
            </span>
          </div>
        )}
      </div>

      {/* Loading Skeleton */}
      {loadingJob && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }} data-testid="job-detail-skeleton">
          <div
            style={{
              height: '140px',
              backgroundColor: 'var(--color-surface)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--color-border)',
              animation: 'pulse 1.5s ease-in-out infinite',
            }}
          />
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 1fr)', gap: '1.5rem' }}>
            <div
              style={{
                height: '400px',
                backgroundColor: 'var(--color-surface)',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--color-border)',
                animation: 'pulse 1.5s ease-in-out infinite',
              }}
            />
            <div
              style={{
                height: '400px',
                backgroundColor: 'var(--color-surface)',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--color-border)',
                animation: 'pulse 1.5s ease-in-out infinite',
              }}
            />
          </div>
        </div>
      )}

      {/* Not Found State (404) */}
      {jobStatusCode === 404 && (
        <div
          className="card"
          style={{ maxWidth: '640px', margin: '3rem auto', textAlign: 'center', padding: '3rem 2rem' }}
          data-testid="job-not-found"
        >
          <div
            style={{
              width: '3.5rem',
              height: '3.5rem',
              borderRadius: '50%',
              background: 'rgba(239, 68, 68, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1.25rem',
              color: 'var(--danger-text)',
            }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
            Job Posting Not Found
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.75rem', fontSize: '0.875rem' }}>
            The requested job posting could not be found or has been unlisted from the platform.
          </p>
          <button type="button" className="btn btn-secondary" onClick={handleBackToDiscovery}>
            ← Back to Job Discovery
          </button>
        </div>
      )}

      {/* General / Auth / Validation Error State */}
      {jobError && jobStatusCode !== 404 && (
        <div style={{ maxWidth: '640px', margin: '2rem auto' }} data-testid="job-detail-error">
          <Alert
            variant="danger"
            title={
              jobStatusCode === 401
                ? 'Unauthorized Access'
                : jobStatusCode === 422
                  ? 'Invalid Job Request'
                  : 'Error Loading Job'
            }
          >
            {jobStatusCode === 401
              ? 'Authentication is required to view this job detail.'
              : jobStatusCode === 422
                ? 'The requested job identifier is malformed or invalid.'
                : jobError}
          </Alert>
          <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem', justifyContent: 'center' }}>
            <button type="button" className="btn btn-primary" onClick={() => fetchJob()}>
              Retry
            </button>
            <button type="button" className="btn btn-secondary" onClick={handleBackToDiscovery}>
              Back to Job Discovery
            </button>
          </div>
        </div>
      )}

      {/* Job Detail & Match View */}
      {!loadingJob && job && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }} data-testid="job-detail-content">
          <JobDetailHeader job={job} />

          {profilesError && (
            <Alert variant="warning" title="Candidate Profiles Notice">
              {profilesError}
            </Alert>
          )}

          {/* 2-Column Responsive Layout */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 360px), 1fr))',
              gap: '1.75rem',
              alignItems: 'start',
            }}
          >
            {/* Left Column: Job Description & Responsibilities */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <JobDetailBody job={job} />
            </div>

            {/* Right Column: Deterministic Match Panel */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <MatchPanel
                jobId={job.id}
                searchProfiles={searchProfiles}
                selectedProfileId={selectedProfileId}
                onSelectProfile={handleSelectProfile}
              />
              <ApplicationTrackingPanel jobId={job.id} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
