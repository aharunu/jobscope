import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { JobDetailClient } from '../app/jobs/[id]/JobDetailClient';
import { MatchPanel } from '../components/matching/MatchPanel';
import { JobCard } from '../components/jobs/JobCard';
import { JobPagination } from '../components/jobs/JobPagination';
import { ApiError, JobDetailResponse, SearchProfileResponse } from '../lib/api/types';

// Mock Next.js navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

const mockGetJobById = vi.fn();
const mockListSearchProfiles = vi.fn();
const mockEvaluateMatch = vi.fn();

vi.mock('../lib/api/jobs', () => ({
  getJobById: (...args: any[]) => mockGetJobById(...args),
}));

vi.mock('../lib/api/search_profiles', () => ({
  listSearchProfiles: (...args: any[]) => mockListSearchProfiles(...args),
}));

vi.mock('../lib/api/matching', () => ({
  evaluateMatch: (...args: any[]) => mockEvaluateMatch(...args),
}));

const mockProfiles: SearchProfileResponse[] = [
  {
    id: 'p-1',
    base_profile_id: 'bp-1',
    name: 'Profile 1',
    target_roles: ['Role 1'],
    seniority: 'Mid',
    target_skills: ['Skill 1'],
    locations: ['Remote'],
    work_modes: ['Remote'],
    industries: ['Tech'],
    salary_min: 100000,
    salary_max: 120000,
    created_at: null,
    updated_at: null,
  },
];

describe('Hardening Edge Cases (Phase 8.3)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('ApiError Helper & 422 Details', () => {
    it('correctly reports error category getters', () => {
      const err404 = new ApiError(404, 'Job not found');
      expect(err404.isNotFound).toBe(true);
      expect(err404.isUnauthorized).toBe(false);

      const err401 = new ApiError(401, 'Unauthorized');
      expect(err401.isUnauthorized).toBe(true);

      const err422 = new ApiError(422, [
        { loc: ['body', 'job_id'], msg: 'Invalid UUID format', type: 'value_error' },
      ]);
      expect(err422.isValidationError).toBe(true);
      expect(err422.message).toContain('Invalid UUID format');

      const err500 = new ApiError(500, 'Server exploded');
      expect(err500.isServerError).toBe(true);
    });
  });

  describe('JobDetail Error & Not Found States', () => {
    it('renders dedicated 404 Not Found card when job does not exist', async () => {
      mockGetJobById.mockRejectedValue(new ApiError(404, 'Job not found'));
      mockListSearchProfiles.mockResolvedValue(mockProfiles);

      render(<JobDetailClient jobId="non-existent-id" />);

      await waitFor(() => {
        expect(screen.getByTestId('job-not-found')).toBeInTheDocument();
        expect(screen.getByText('Job Posting Not Found')).toBeInTheDocument();
        expect(screen.getByText(/The requested job posting could not be found/i)).toBeInTheDocument();
      });
    });

    it('renders 401 Unauthorized alert state', async () => {
      mockGetJobById.mockRejectedValue(new ApiError(401, 'Unauthorized'));
      mockListSearchProfiles.mockResolvedValue(mockProfiles);

      render(<JobDetailClient jobId="restricted-job-id" />);

      await waitFor(() => {
        expect(screen.getByTestId('job-detail-error')).toBeInTheDocument();
        expect(screen.getByText('Unauthorized Access')).toBeInTheDocument();
      });
    });

    it('renders 422 Invalid Job Request alert state', async () => {
      mockGetJobById.mockRejectedValue(new ApiError(422, 'Validation error'));
      mockListSearchProfiles.mockResolvedValue(mockProfiles);

      render(<JobDetailClient jobId="invalid-uuid" />);

      await waitFor(() => {
        expect(screen.getByTestId('job-detail-error')).toBeInTheDocument();
        expect(screen.getByText('Invalid Job Request')).toBeInTheDocument();
      });
    });
  });

  describe('Job with Null / Missing Optional Fields', () => {
    const minimalJob: JobDetailResponse = {
      id: 'job-minimal',
      source_id: 'src-1',
      canonical_url: '', // Missing
      company: 'Stealth Startup',
      title: 'Founding Engineer',
      description: '', // Missing / empty
      responsibilities: null, // Missing
      status: 'ACTIVE',
      external_job_id: null,
      location: null, // Missing
      work_mode: null, // Missing
      employment_type: null, // Missing
      salary: null, // Missing
      published_at: null,
      first_seen_at: '2026-09-01T00:00:00Z',
      last_seen_at: '2026-09-29T00:00:00Z',
      closed_at: null,
      created_at: '2026-09-01T00:00:00Z',
      updated_at: '2026-09-29T00:00:00Z',
      source_name: null,
      ats_type: null,
      source_url: 'https://stealth.com',
      content_hash: 'abcdef1234567890abcdef1234567890',
    };

    it('renders JobCard safely with null salary, missing work mode, and unavailable apply link', () => {
      render(<JobCard job={minimalJob} />);

      expect(screen.getByText('Stealth Startup')).toBeInTheDocument();
      expect(screen.getByText('Founding Engineer')).toBeInTheDocument();
      expect(screen.getByText('Not specified')).toBeInTheDocument();
      expect(screen.getByText('Direct apply unavailable')).toBeInTheDocument();
      // Must NOT invent "Remote" when work_mode is null
      expect(screen.queryByText('Remote')).not.toBeInTheDocument();
    });

    it('renders JobDetailClient safely with null fields and empty description fallback', async () => {
      mockGetJobById.mockResolvedValue(minimalJob);
      mockListSearchProfiles.mockResolvedValue(mockProfiles);

      render(<JobDetailClient jobId="job-minimal" />);

      await waitFor(() => {
        expect(screen.getByText('Stealth Startup')).toBeInTheDocument();
        expect(screen.getByText('No detailed description provided.')).toBeInTheDocument();
        expect(screen.getByText('Apply link unavailable')).toBeInTheDocument();
        // Responsibilities section must NOT be rendered when null
        expect(screen.queryByText('Responsibilities')).not.toBeInTheDocument();
      });
    });
  });

  describe('MatchPanel Error Handling & Retry', () => {
    it('displays error and allows user to retry match evaluation', async () => {
      mockEvaluateMatch
        .mockRejectedValueOnce(new ApiError(500, 'Match Engine timeout'))
        .mockResolvedValueOnce({
          id: 'm-1',
          job_id: 'job-1',
          base_profile_id: 'bp-1',
          search_profile_id: 'p-1',
          overall_score: 80.0,
          deterministic_score: 80.0,
          final_score: 80.0,
          confidence: 85.0,
          category_scores: {},
          requirement_matches: [],
          explanation: null,
          created_at: null,
          updated_at: null,
        });

      render(
        <MatchPanel
          jobId="job-1"
          searchProfiles={mockProfiles}
          selectedProfileId="p-1"
          onSelectProfile={vi.fn()}
        />
      );

      // Error shown
      await waitFor(() => {
        expect(screen.getByTestId('match-error-container')).toBeInTheDocument();
        expect(screen.getByText('Retry Match Evaluation')).toBeInTheDocument();
      });

      // User clicks retry
      const retryBtn = screen.getByText('Retry Match Evaluation');
      fireEvent.click(retryBtn);

      // Successfully recovers
      await waitFor(() => {
        expect(screen.getByText('80')).toBeInTheDocument();
      });
    });
  });

  describe('Pagination Edge Cases', () => {
    it('safely handles zero or negative limits and out-of-bounds offsets', () => {
      const handlePage = vi.fn();
      const handleLimit = vi.fn();

      render(
        <JobPagination
          total={50}
          limit={0} // invalid limit
          offset={-10} // invalid offset
          onPageChange={handlePage}
          onLimitChange={handleLimit}
        />
      );

      // Safe limit defaults to 20, safe offset defaults to 0 -> Page 1 of 3
      expect(screen.getByText('Page 1 of 3')).toBeInTheDocument();
      expect(screen.getByText(/Showing/)).toBeInTheDocument();
    });
  });
});
