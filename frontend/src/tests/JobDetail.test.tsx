import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { JobDetailHeader } from '../components/jobs/JobDetailHeader';
import { JobDetailBody } from '../components/jobs/JobDetailBody';
import { JobDetailClient } from '../app/jobs/[id]/JobDetailClient';
import { JobDetailResponse, SearchProfileResponse } from '../lib/api/types';

// Mock Next.js navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

// Mock API clients
const mockGetJobById = vi.fn();
const mockListSearchProfiles = vi.fn();
const mockEvaluateMatch = vi.fn();
const mockGetSavedMatch = vi.fn();

vi.mock('../lib/api/jobs', () => ({
  getJobById: (...args: any[]) => mockGetJobById(...args),
}));

vi.mock('../lib/api/search_profiles', () => ({
  listSearchProfiles: (...args: any[]) => mockListSearchProfiles(...args),
}));

vi.mock('../lib/api/matching', () => ({
  evaluateMatch: (...args: any[]) => mockEvaluateMatch(...args),
  getSavedMatch: (...args: any[]) => mockGetSavedMatch(...args),
}));

const mockJobDetail: JobDetailResponse = {
  id: 'job-123',
  source_id: 'source-123',
  canonical_url: 'https://careers.google.com/jobs/results/12345',
  company: 'Google',
  title: 'Staff Software Engineer',
  description: 'Detailed description of the role, designing distributed infrastructure.',
  responsibilities: 'Lead architecture designs.\nMentor junior engineers.',
  status: 'ACTIVE',
  external_job_id: 'G-12345',
  location: 'Zurich, Switzerland',
  work_mode: 'Hybrid',
  employment_type: 'Full-time',
  salary: 'CHF 180,000 - CHF 220,000',
  published_at: '2026-09-01T10:00:00Z',
  first_seen_at: '2026-09-01T10:00:00Z',
  last_seen_at: '2026-09-29T10:00:00Z',
  closed_at: null,
  created_at: '2026-09-01T10:00:00Z',
  updated_at: '2026-09-29T10:00:00Z',
  source_name: 'Google Careers',
  ats_type: 'custom',
  source_url: 'https://careers.google.com',
  content_hash: 'abcdef1234567890abcdef1234567890',
};

const mockProfiles: SearchProfileResponse[] = [
  {
    id: 'profile-alpha',
    base_profile_id: 'bp-1',
    name: 'Backend Profile',
    target_roles: ['Backend Engineer'],
    seniority: 'Senior',
    target_skills: ['Python', 'Distributed Systems'],
    locations: ['Zurich', 'Remote'],
    work_modes: ['Hybrid', 'Remote'],
    industries: ['Tech'],
    salary_min: 150000,
    salary_max: 230000,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'profile-beta',
    base_profile_id: 'bp-1',
    name: 'Fullstack Profile',
    target_roles: ['Fullstack Engineer'],
    seniority: 'Staff',
    target_skills: ['TypeScript', 'React'],
    locations: ['Remote'],
    work_modes: ['Remote'],
    industries: ['Tech'],
    salary_min: 140000,
    salary_max: 200000,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

describe('JobDetail Components', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  describe('JobDetailHeader', () => {
    it('renders metadata and external apply link with security attributes', () => {
      render(<JobDetailHeader job={mockJobDetail} />);

      expect(screen.getByText('Google')).toBeInTheDocument();
      expect(screen.getByText('Staff Software Engineer')).toBeInTheDocument();
      expect(screen.getByText('Zurich, Switzerland')).toBeInTheDocument();
      expect(screen.getByText('Hybrid')).toBeInTheDocument();
      expect(screen.getByText('Active')).toBeInTheDocument();
      expect(screen.getByText('CHF 180,000 - CHF 220,000')).toBeInTheDocument();

      const applyLink = screen.getByRole('link', { name: /apply on company/i });
      expect(applyLink).toHaveAttribute('href', 'https://careers.google.com/jobs/results/12345');
      expect(applyLink).toHaveAttribute('target', '_blank');
      expect(applyLink).toHaveAttribute('rel', 'noopener noreferrer');
    });
  });

  describe('JobDetailBody', () => {
    it('renders responsibilities only when provided by the backend', () => {
      const { rerender } = render(<JobDetailBody job={mockJobDetail} />);

      expect(screen.getByText('Responsibilities')).toBeInTheDocument();
      expect(screen.getByText(/Lead architecture designs/i)).toBeInTheDocument();

      // When responsibilities is null or empty, responsibilities section must NOT be rendered
      const jobWithoutResponsibilities = { ...mockJobDetail, responsibilities: null };
      rerender(<JobDetailBody job={jobWithoutResponsibilities} />);
      expect(screen.queryByText('Responsibilities')).not.toBeInTheDocument();
    });

    it('renders description and canonical metadata', () => {
      render(<JobDetailBody job={mockJobDetail} />);

      expect(screen.getByText('Job Description')).toBeInTheDocument();
      expect(screen.getByText(/Detailed description of the role/i)).toBeInTheDocument();
      expect(screen.getByText('Canonical Metadata')).toBeInTheDocument();
      expect(screen.getByText('G-12345')).toBeInTheDocument();
    });

    it('does not display raw JSON payload in UI and extracts clean description, responsibilities, and requirements', () => {
      const rawJsonJob: JobDetailResponse = {
        ...mockJobDetail,
        description: JSON.stringify({
          descriptionPlain: 'We are seeking an experienced Backend Engineer to scale our services.',
          descriptionBody: '<div>We are seeking an experienced Backend Engineer</div>',
          descriptionBodyPlain: 'We are seeking an experienced Backend Engineer to scale our services.',
          lists: [
            {
              text: 'Responsibilities',
              content: '<li>Design scalable distributed systems</li><li>Optimize PostgreSQL database queries</li>',
            },
            {
              text: 'Requirements',
              content: '<li>5+ years Python or Go experience</li><li>Deep understanding of Clean Architecture</li>',
            },
          ],
          hostedUrl: 'https://jobs.lever.co/example/123',
          applyUrl: 'https://jobs.lever.co/example/123/apply',
          id: 'lever-ext-id-999',
        }),
        responsibilities: null,
      };

      render(<JobDetailBody job={rawJsonJob} />);

      // Verify raw JSON keys are NEVER visible in the DOM
      expect(screen.queryByText(/descriptionPlain/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/descriptionBody/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/hostedUrl/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/applyUrl/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/lever-ext-id-999/i)).not.toBeInTheDocument();

      // Verify clean description text is rendered
      expect(
        screen.getByText(/We are seeking an experienced Backend Engineer to scale our services/i)
      ).toBeInTheDocument();

      // Verify extracted Responsibilities section
      expect(screen.getByText('Responsibilities')).toBeInTheDocument();
      expect(screen.getByText(/Design scalable distributed systems/i)).toBeInTheDocument();
      expect(screen.getByText(/Optimize PostgreSQL database queries/i)).toBeInTheDocument();

      // Verify extracted Requirements section
      expect(screen.getByText('Requirements')).toBeInTheDocument();
      expect(screen.getByText(/5\+ years Python or Go experience/i)).toBeInTheDocument();

      // Verify Canonical Metadata is still present and untampered
      expect(screen.getByText('Canonical Metadata')).toBeInTheDocument();
      expect(screen.getByText('G-12345')).toBeInTheDocument();
    });

    it('renders HTML content without displaying raw HTML tags, unescapes entities and formats links safely', () => {
      const htmlJob: JobDetailResponse = {
        ...mockJobDetail,
        description:
          '<p><strong class="highlight">About Us:</strong></p><p>We build disruptive gaming experiences.<br>&nbsp;Learn more on our <a href="https://example.com/team">team page</a>.</p>',
      };

      render(<JobDetailBody job={htmlJob} />);

      // Verify text content is visible
      expect(screen.getByText(/About Us:/i)).toBeInTheDocument();
      expect(screen.getByText(/We build disruptive gaming experiences/i)).toBeInTheDocument();

      // Verify raw tags and escaped entities are NOT displayed as literal text
      expect(screen.queryByText(/<p>/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/<\/p>/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/<strong>/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/&nbsp;/i)).not.toBeInTheDocument();

      // Verify link has safe security attributes
      const teamLink = screen.getByRole('link', { name: /team page/i });
      expect(teamLink).toHaveAttribute('href', 'https://example.com/team');
      expect(teamLink).toHaveAttribute('target', '_blank');
      expect(teamLink).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('handles null, empty, and whitespace description with graceful fallback', () => {
      const emptyJob: JobDetailResponse = {
        ...mockJobDetail,
        description: '   ',
        responsibilities: null,
      };

      render(<JobDetailBody job={emptyJob} />);
      expect(screen.getByText('No detailed description provided.')).toBeInTheDocument();
      expect(screen.queryByText('Responsibilities')).not.toBeInTheDocument();
    });
  });

  describe('JobDetailClient & Precedence', () => {
    it('selects profile according to precedence: URL query -> localStorage -> first profile', async () => {
      mockGetJobById.mockResolvedValue(mockJobDetail);
      mockListSearchProfiles.mockResolvedValue(mockProfiles);
      mockGetSavedMatch.mockResolvedValue({
        id: 'match-1',
        job_id: 'job-123',
        base_profile_id: 'bp-1',
        search_profile_id: 'profile-beta',
        overall_score: 88.0,
        deterministic_score: 88.0,
        final_score: 88.0,
        confidence: 90.0,
        category_scores: { ROLE: 0.9, SKILLS: 0.8 },
        requirement_matches: [],
        explanation: {
          summary: 'High fit',
          matched_skills: ['TypeScript'],
          missing_skills: [],
          partial_matches: [],
          role_result: 'MATCHED',
          experience_result: 'MATCHED',
          education_result: 'MATCHED',
          location_result: 'MATCHED',
          blockers: [],
          unknowns: [],
          category_explanations: {},
        },
        created_at: null,
        updated_at: null,
      });

      // 1. URL profile precedence
      render(<JobDetailClient jobId="job-123" initialProfileQuery="profile-beta" />);

      await waitFor(() => {
        expect(screen.getByTestId('search-profile-selector')).toHaveValue('profile-beta');
      });
    });

    it('falls back to localStorage profile when URL query is absent or invalid', async () => {
      localStorage.setItem('jobscope_selected_profile_id', 'profile-beta');
      mockGetJobById.mockResolvedValue(mockJobDetail);
      mockListSearchProfiles.mockResolvedValue(mockProfiles);
      mockGetSavedMatch.mockResolvedValue({
        id: 'match-1',
        job_id: 'job-123',
        base_profile_id: 'bp-1',
        search_profile_id: 'profile-beta',
        overall_score: 85.0,
        deterministic_score: 85.0,
        final_score: 85.0,
        confidence: 90.0,
        category_scores: {},
        requirement_matches: [],
        explanation: null,
        created_at: null,
        updated_at: null,
      });

      render(<JobDetailClient jobId="job-123" initialProfileQuery="invalid-profile-id" />);

      await waitFor(() => {
        expect(screen.getByTestId('search-profile-selector')).toHaveValue('profile-beta');
      });
    });

    it('falls back to first profile when neither URL nor localStorage has valid profile', async () => {
      mockGetJobById.mockResolvedValue(mockJobDetail);
      mockListSearchProfiles.mockResolvedValue(mockProfiles);
      mockGetSavedMatch.mockResolvedValue({
        id: 'match-1',
        job_id: 'job-123',
        base_profile_id: 'bp-1',
        search_profile_id: 'profile-alpha',
        overall_score: 75.0,
        deterministic_score: 75.0,
        final_score: 75.0,
        confidence: 85.0,
        category_scores: {},
        requirement_matches: [],
        explanation: null,
        created_at: null,
        updated_at: null,
      });

      render(<JobDetailClient jobId="job-123" />);

      await waitFor(() => {
        expect(screen.getByTestId('search-profile-selector')).toHaveValue('profile-alpha');
      });
    });

    it('preserves discovery URL state on back button click', async () => {
      sessionStorage.setItem('jobscope_last_discovery_url', '/jobs?q=architect&work_mode=remote&offset=20');
      mockGetJobById.mockResolvedValue(mockJobDetail);
      mockListSearchProfiles.mockResolvedValue(mockProfiles);

      render(<JobDetailClient jobId="job-123" />);

      await waitFor(() => {
        expect(screen.getByTestId('back-to-discovery')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('back-to-discovery'));
      expect(mockPush).toHaveBeenCalledWith('/jobs?q=architect&work_mode=remote&offset=20');
    });
  });
});
