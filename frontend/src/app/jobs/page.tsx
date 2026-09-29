'use client';

import React, { useState, useEffect, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { listJobs } from '../../lib/api/jobs';
import { JobFilterParams, JobSummaryResponse } from '../../lib/api/types';
import { DEFAULT_PAGE_SIZE } from '../../lib/constants';
import { JobSearchInput } from '../../components/jobs/JobSearchInput';
import { JobFilters } from '../../components/jobs/JobFilters';
import { JobList } from '../../components/jobs/JobList';
import { JobPagination } from '../../components/jobs/JobPagination';
import { Spinner } from '../../components/ui/Spinner';

function JobsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Parse filters from URL
  const initialQ = searchParams.get('q') || '';
  const initialStatus = searchParams.get('status') || '';
  const initialWorkMode = searchParams.get('work_mode') || '';
  const initialEmploymentType = searchParams.get('employment_type') || '';
  const initialAtsType = searchParams.get('ats_type') || '';
  const initialCompany = searchParams.get('company') || '';
  const initialLocation = searchParams.get('location') || '';
  const initialLimit = Number(searchParams.get('limit')) || DEFAULT_PAGE_SIZE;
  const initialOffset = Number(searchParams.get('offset')) || 0;

  const [filters, setFilters] = useState<JobFilterParams>({
    q: initialQ,
    status: initialStatus,
    work_mode: initialWorkMode,
    employment_type: initialEmploymentType,
    ats_type: initialAtsType,
    company: initialCompany,
    location: initialLocation,
    limit: initialLimit,
    offset: initialOffset,
  });

  const [jobs, setJobs] = useState<JobSummaryResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Sync filters from URL search parameters (handles browser Back/Forward & refresh)
  useEffect(() => {
    const q = searchParams.get('q') || '';
    const status = searchParams.get('status') || '';
    const work_mode = searchParams.get('work_mode') || '';
    const employment_type = searchParams.get('employment_type') || '';
    const ats_type = searchParams.get('ats_type') || '';
    const company = searchParams.get('company') || '';
    const location = searchParams.get('location') || '';
    const rawLimit = Number(searchParams.get('limit'));
    const limit = rawLimit > 0 ? rawLimit : DEFAULT_PAGE_SIZE;
    const rawOffset = Number(searchParams.get('offset'));
    const offset = !isNaN(rawOffset) && rawOffset >= 0 ? rawOffset : 0;

    setFilters((prev) => {
      if (
        (prev.q || '') === q &&
        (prev.status || '') === status &&
        (prev.work_mode || '') === work_mode &&
        (prev.employment_type || '') === employment_type &&
        (prev.ats_type || '') === ats_type &&
        (prev.company || '') === company &&
        (prev.location || '') === location &&
        (prev.limit || DEFAULT_PAGE_SIZE) === limit &&
        (prev.offset || 0) === offset
      ) {
        return prev;
      }
      return {
        q: q || undefined,
        status: status || undefined,
        work_mode: work_mode || undefined,
        employment_type: employment_type || undefined,
        ats_type: ats_type || undefined,
        company: company || undefined,
        location: location || undefined,
        limit,
        offset,
      };
    });
  }, [searchParams]);

  // Sync state to URL search parameters
  const updateUrlParams = useCallback(
    (newFilters: JobFilterParams) => {
      const params = new URLSearchParams();
      if (newFilters.q) params.set('q', newFilters.q);
      if (newFilters.status) params.set('status', newFilters.status);
      if (newFilters.work_mode) params.set('work_mode', newFilters.work_mode);
      if (newFilters.employment_type) params.set('employment_type', newFilters.employment_type);
      if (newFilters.ats_type) params.set('ats_type', newFilters.ats_type);
      if (newFilters.company) params.set('company', newFilters.company);
      if (newFilters.location) params.set('location', newFilters.location);
      if (newFilters.limit && newFilters.limit !== DEFAULT_PAGE_SIZE) {
        params.set('limit', String(newFilters.limit));
      }
      if (newFilters.offset && newFilters.offset > 0) {
        params.set('offset', String(newFilters.offset));
      }

      const queryString = params.toString();
      const targetUrl = queryString ? `/jobs?${queryString}` : '/jobs';
      if (typeof window !== 'undefined') {
        try {
          sessionStorage.setItem('jobscope_last_discovery_url', targetUrl);
        } catch {
          // Ignore storage quota or access issues
        }
      }
      router.replace(targetUrl, { scroll: false });
    },
    [router]
  );

  // Fetch jobs with AbortController for search/filter cancellation
  const fetchJobsData = useCallback(async (currentFilters: JobFilterParams, signal?: AbortSignal) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await listJobs(currentFilters, signal);
      setJobs(res.jobs);
      setTotal(res.total);
    } catch (err: unknown) {
      if ((err instanceof DOMException || err instanceof Error) && err.name === 'AbortError') {
        // Ignored: intentional request cancellation from fast typing/filtering
        return;
      }
      setError(err instanceof Error ? err.message : 'An error occurred while loading jobs.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Trigger fetch and URL update on filter changes
  useEffect(() => {
    const controller = new AbortController();
    fetchJobsData(filters, controller.signal);
    updateUrlParams(filters);

    return () => {
      controller.abort();
    };
  }, [filters, fetchJobsData, updateUrlParams]);

  // Handlers for filter mutations
  const handleSearchChange = (newQ: string) => {
    setFilters((prev) => ({
      ...prev,
      q: newQ || undefined,
      offset: 0, // Reset to first page
    }));
  };

  const handleFilterChange = (updated: Partial<JobFilterParams>) => {
    setFilters((prev) => ({
      ...prev,
      ...updated,
      offset: 0, // Reset to first page
    }));
  };

  const handleResetFilters = () => {
    setFilters({
      q: undefined,
      status: undefined,
      work_mode: undefined,
      employment_type: undefined,
      ats_type: undefined,
      company: undefined,
      location: undefined,
      limit: filters.limit || DEFAULT_PAGE_SIZE,
      offset: 0,
    });
  };

  const handlePageChange = (newOffset: number) => {
    setFilters((prev) => ({
      ...prev,
      offset: newOffset,
    }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleLimitChange = (newLimit: number) => {
    setFilters((prev) => ({
      ...prev,
      limit: newLimit,
      offset: 0,
    }));
  };

  const hasActiveFilters = Boolean(
    filters.q ||
      filters.status ||
      filters.work_mode ||
      filters.employment_type ||
      filters.ats_type ||
      filters.company ||
      filters.location
  );

  return (
    <div className="container" style={{ paddingTop: '2rem' }}>
      {/* Page Title & Search Bar */}
      <section style={{ marginBottom: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div>
          <h1
            style={{
              fontSize: '2rem',
              fontWeight: 800,
              letterSpacing: '-0.03em',
              color: 'var(--text-primary)',
              marginBottom: '0.4rem',
            }}
          >
            Job Discovery
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem' }}>
            Explore verified canonical job postings crawled from integrated ATS platforms.
          </p>
        </div>

        <div style={{ maxWidth: '720px' }}>
          <JobSearchInput value={filters.q || ''} onChange={handleSearchChange} />
        </div>
      </section>

      {/* Multi-attribute Filters */}
      <section style={{ marginBottom: '1.75rem' }}>
        <JobFilters
          filters={filters}
          onChange={handleFilterChange}
          onReset={handleResetFilters}
        />
      </section>

      {/* Jobs Grid or Empty/Loading/Error View */}
      <section>
        <JobList
          jobs={jobs}
          isLoading={isLoading}
          error={error}
          onRetry={() => fetchJobsData(filters)}
          hasActiveFilters={hasActiveFilters}
          onResetFilters={handleResetFilters}
        />

        {/* Bounded Pagination Controls */}
        {!isLoading && !error && jobs.length > 0 && (
          <JobPagination
            total={total}
            limit={filters.limit || DEFAULT_PAGE_SIZE}
            offset={filters.offset || 0}
            onPageChange={handlePageChange}
            onLimitChange={handleLimitChange}
          />
        )}
      </section>
    </div>
  );
}

export default function JobsPage() {
  return (
    <Suspense
      fallback={
        <div style={{ display: 'flex', justifyContent: 'center', padding: '5rem 0' }}>
          <Spinner size="lg" label="Loading Job Discovery..." />
        </div>
      }
    >
      <JobsContent />
    </Suspense>
  );
}
