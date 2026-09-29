import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import JobsPage from '../app/jobs/page';
import { JobDetailClient } from '../app/jobs/[id]/JobDetailClient';
import { MatchPanel } from '../components/matching/MatchPanel';
import { JobSummaryResponse, JobDetailResponse, SearchProfileResponse, MatchResultResponse } from '../lib/api/types';

// Mock Next.js navigation with stable router instance
const mockPush = vi.fn();
const mockReplace = vi.fn();
const mockRouter = {
  push: mockPush,
  replace: mockReplace,
};
let mockSearchParams = new URLSearchParams();

vi.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
  useSearchParams: () => mockSearchParams,
}));

// Mock APIs
const mockListJobs = vi.fn();
const mockGetJobById = vi.fn();
const mockListSearchProfiles = vi.fn();
const mockEvaluateMatch = vi.fn();

vi.mock('../lib/api/jobs', () => ({
  listJobs: (...args: any[]) => mockListJobs(...args),
  getJobById: (...args: any[]) => mockGetJobById(...args),
}));

vi.mock('../lib/api/search_profiles', () => ({
  listSearchProfiles: (...args: any[]) => mockListSearchProfiles(...args),
}));

vi.mock('../lib/api/matching', () => ({
  evaluateMatch: (...args: any[]) => mockEvaluateMatch(...args),
}));

const mockJobs: JobSummaryResponse[] = [
  {
    id: 'job-101',
    source_id: 'src-1',
    canonical_url: 'https://company.com/job/101',
    company: 'Stripe',
    title: 'Staff Infrastructure Engineer',
    status: 'ACTIVE',
    external_job_id: 'st-101',
    location: 'Remote, US',
    work_mode: 'Remote',
    employment_type: 'Full-time',
    salary: '$220,000 - $260,000',
    published_at: '2026-09-01T12:00:00Z',
    first_seen_at: '2026-09-01T12:00:00Z',
    last_seen_at: '2026-09-29T12:00:00Z',
    closed_at: null,
    created_at: '2026-09-01T12:00:00Z',
    updated_at: '2026-09-29T12:00:00Z',
    source_name: 'Stripe Careers',
    ats_type: 'greenhouse',
    source_url: 'https://stripe.com',
  },
];

const mockJobDetail: JobDetailResponse = {
  ...mockJobs[0],
  description: 'Design and build resilient planetary infrastructure systems.',
  responsibilities: 'Lead architecture designs.\nOversee distributed consensus pipelines.',
  content_hash: '1234567890abcdef1234567890abcdef',
};

const mockProfiles: SearchProfileResponse[] = [
  {
    id: 'profile-a',
    base_profile_id: 'bp-1',
    name: 'Profile A: Infra Lead',
    target_roles: ['Infrastructure Engineer'],
    seniority: 'Staff',
    target_skills: ['Go', 'Kubernetes'],
    locations: ['Remote'],
    work_modes: ['Remote'],
    industries: ['FinTech'],
    salary_min: 200000,
    salary_max: 280000,
    created_at: null,
    updated_at: null,
  },
  {
    id: 'profile-b',
    base_profile_id: 'bp-1',
    name: 'Profile B: Frontend Specialist',
    target_roles: ['Frontend Engineer'],
    seniority: 'Senior',
    target_skills: ['React', 'CSS'],
    locations: ['New York'],
    work_modes: ['Hybrid'],
    industries: ['Design'],
    salary_min: 150000,
    salary_max: 190000,
    created_at: null,
    updated_at: null,
  },
];

const matchResultA: MatchResultResponse = {
  id: 'match-a',
  job_id: 'job-101',
  base_profile_id: 'bp-1',
  search_profile_id: 'profile-a',
  overall_score: 94.0,
  deterministic_score: 94.0,
  final_score: 94.0,
  confidence: 96.0,
  category_scores: { ROLE: 1.0, SKILLS: 0.9, EXPERIENCE: 0.95 },
  requirement_matches: [
    {
      id: 'rm-1',
      requirement_id: 'req-1',
      match_status: 'MATCHED',
      score: 1.0,
      reason: '10 years infrastructure experience matches requirement.',
      evidence: 'Principal Engineer at CloudCorp',
      is_blocker: false,
    },
  ],
  explanation: {
    summary: 'Exceptional alignment across all dimensions.',
    matched_skills: ['Kubernetes', 'Go'],
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
};

const matchResultB: MatchResultResponse = {
  id: 'match-b',
  job_id: 'job-101',
  base_profile_id: 'bp-1',
  search_profile_id: 'profile-b',
  overall_score: 45.0,
  deterministic_score: 45.0,
  final_score: 45.0,
  confidence: 80.0,
  category_scores: { ROLE: 0.4, SKILLS: 0.3, EXPERIENCE: 0.6 },
  requirement_matches: [
    {
      id: 'rm-2',
      requirement_id: 'req-1',
      match_status: 'NOT_MATCHED',
      score: 0.2,
      reason: 'Lacks distributed systems and Go background.',
      evidence: null,
      is_blocker: false,
    },
  ],
  explanation: {
    summary: 'Low alignment for specialized infrastructure position.',
    matched_skills: [],
    missing_skills: ['Go', 'Kubernetes'],
    partial_matches: [],
    role_result: 'NOT_MATCHED',
    experience_result: 'PARTIAL',
    education_result: 'MATCHED',
    location_result: 'NOT_MATCHED',
    blockers: [],
    unknowns: [],
    category_explanations: {},
  },
  created_at: null,
  updated_at: null,
};

describe('Comprehensive User Flows (Phase 8.3)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    mockSearchParams = new URLSearchParams();
  });

  it('FLOW 1: Open /jobs -> search -> filter -> paginate -> open job card', async () => {
    mockListJobs.mockResolvedValue({ jobs: mockJobs, total: 100 });

    render(<JobsPage />);

    // 1. Initial list rendered
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: /Staff Infrastructure Engineer/i })).toBeInTheDocument();
    });

    // 2. Search query change
    const searchInput = screen.getByLabelText(/search jobs by title or company/i);
    fireEvent.change(searchInput, { target: { value: 'Staff' } });

    // 3. Filter change
    const workModeSelect = screen.getByLabelText(/work mode/i);
    fireEvent.change(workModeSelect, { target: { value: 'Remote' } });

    // 4. Pagination Next (wait for loading to finish)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /next page/i })).toBeInTheDocument();
    });
    const nextBtn = screen.getByRole('button', { name: /next page/i });
    fireEvent.click(nextBtn);

    // 5. Open job card (wait for page 2 load)
    await waitFor(() => {
      expect(
        screen.getByRole('link', { name: /view details for Staff Infrastructure Engineer at Stripe/i })
      ).toBeInTheDocument();
    });
    const jobCard = screen.getByRole('link', { name: /view details for Staff Infrastructure Engineer at Stripe/i });
    fireEvent.click(jobCard);

    expect(mockPush).toHaveBeenCalledWith('/jobs/job-101');
  });

  it('FLOW 2: Open job detail -> select Search Profile -> Evaluate Match -> inspect result', async () => {
    mockGetJobById.mockResolvedValue(mockJobDetail);
    mockListSearchProfiles.mockResolvedValue(mockProfiles);
    mockEvaluateMatch.mockResolvedValue(matchResultA);

    render(<JobDetailClient jobId="job-101" />);

    // 1. Job details render
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /Staff Infrastructure Engineer/i })).toBeInTheDocument();
      expect(screen.getByText(/Design and build resilient planetary infrastructure systems/i)).toBeInTheDocument();
      expect(screen.getByText('Responsibilities')).toBeInTheDocument();
    });

    // 2. Profile evaluated and match results rendered
    await waitFor(() => {
      expect(screen.getByText('94')).toBeInTheDocument();
      expect(screen.getByText('Strong Alignment')).toBeInTheDocument();
      expect(screen.getByText('96%')).toBeInTheDocument();
      expect(screen.getByText('✓ Kubernetes')).toBeInTheDocument();
      expect(screen.getByText('✓ Go')).toBeInTheDocument();
      expect(screen.getByText(/10 years infrastructure experience matches requirement/i)).toBeInTheDocument();
    });
  });

  it('FLOW 3: Open job detail -> evaluate Profile A -> switch to Profile B -> verify isolation -> evaluate Profile B', async () => {
    mockEvaluateMatch.mockImplementation(async (payload) => {
      if (payload.search_profile_id === 'profile-a') return matchResultA;
      if (payload.search_profile_id === 'profile-b') return matchResultB;
      throw new Error('Unknown profile');
    });

    const handleSelectProfile = vi.fn();

    const { rerender } = render(
      <MatchPanel
        jobId="job-101"
        searchProfiles={mockProfiles}
        selectedProfileId="profile-a"
        onSelectProfile={handleSelectProfile}
        initialMatchResult={matchResultA}
      />
    );

    // 1. Profile A result shown
    expect(screen.getByText('94')).toBeInTheDocument();
    expect(screen.getByText('Strong Alignment')).toBeInTheDocument();
    expect(screen.getByText('✓ Go')).toBeInTheDocument();

    // 2. User switches to Profile B
    const selector = screen.getByTestId('search-profile-selector');
    fireEvent.change(selector, { target: { value: 'profile-b' } });
    expect(handleSelectProfile).toHaveBeenCalledWith('profile-b');

    // Re-render with new selectedProfileId as parent component would do
    rerender(
      <MatchPanel
        jobId="job-101"
        searchProfiles={mockProfiles}
        selectedProfileId="profile-b"
        onSelectProfile={handleSelectProfile}
      />
    );

    // 3. Strict isolation: Profile A's 94 score and skills MUST NOT be shown under Profile B!
    expect(screen.queryByText('94')).not.toBeInTheDocument();
    expect(screen.queryByText('Strong Alignment')).not.toBeInTheDocument();

    // 4. Profile B evaluated and rendered
    await waitFor(() => {
      expect(screen.getByText('45')).toBeInTheDocument();
      expect(screen.getByText('Low Alignment')).toBeInTheDocument();
      expect(screen.getByText('✕ Go')).toBeInTheDocument();
      expect(screen.getByText('✕ Kubernetes')).toBeInTheDocument();
    });
  });

  it('FLOW 4: Open filtered /jobs state -> open job -> go back -> verify discovery state preserved', async () => {
    sessionStorage.setItem('jobscope_last_discovery_url', '/jobs?q=Infrastructure&work_mode=Remote&limit=20&offset=0');
    mockGetJobById.mockResolvedValue(mockJobDetail);
    mockListSearchProfiles.mockResolvedValue(mockProfiles);

    render(<JobDetailClient jobId="job-101" />);

    await waitFor(() => {
      expect(screen.getByTestId('back-to-discovery')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('back-to-discovery'));

    expect(mockPush).toHaveBeenCalledWith('/jobs?q=Infrastructure&work_mode=Remote&limit=20&offset=0');
  });
});
