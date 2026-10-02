import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SearchProfilesClient } from '../app/search-profiles/SearchProfilesClient';
import { CreateSearchProfileClient } from '../app/search-profiles/new/CreateSearchProfileClient';
import { JobDetailClient } from '../app/jobs/[id]/JobDetailClient';
import { SearchProfileSelector } from '../components/search_profile/SearchProfileSelector';
import { MatchPanel } from '../components/matching/MatchPanel';
import { ApiError, SearchProfileResponse, JobDetailResponse } from '../lib/api/types';

// Mock Next.js navigation
const mockPush = vi.fn();
let mockSearchParamsGet = vi.fn((key: string) => (key === 'returnUrl' ? null : null));

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useSearchParams: () => ({
    get: (key: string) => mockSearchParamsGet(key),
  }),
}));

// Mock API clients
const mockListSearchProfiles = vi.fn();
const mockCreateSearchProfile = vi.fn();
const mockDeleteSearchProfile = vi.fn();
const mockGetJobById = vi.fn();
const mockEvaluateMatch = vi.fn();
const mockGetSavedMatch = vi.fn();

vi.mock('../lib/api/search_profiles', () => ({
  listSearchProfiles: (...args: any[]) => mockListSearchProfiles(...args),
  createSearchProfile: (...args: any[]) => mockCreateSearchProfile(...args),
  deleteSearchProfile: (...args: any[]) => mockDeleteSearchProfile(...args),
}));

vi.mock('../lib/api/jobs', () => ({
  getJobById: (...args: any[]) => mockGetJobById(...args),
}));

vi.mock('../lib/api/matching', () => ({
  evaluateMatch: (...args: any[]) => mockEvaluateMatch(...args),
  getSavedMatch: (...args: any[]) => mockGetSavedMatch(...args),
}));

const mockSingleProfile: SearchProfileResponse = {
  id: 'sp-1',
  base_profile_id: 'bp-1',
  name: 'Senior Python Engineer',
  target_roles: ['Backend Engineer', 'Python Dev'],
  seniority: 'Senior',
  target_skills: ['Python', 'FastAPI', 'PostgreSQL'],
  locations: ['Remote', 'Zurich'],
  work_modes: ['Remote'],
  industries: ['FinTech'],
  salary_min: 130000,
  salary_max: 180000,
  created_at: '2026-09-01T00:00:00Z',
  updated_at: '2026-09-01T00:00:00Z',
};

const mockJob: JobDetailResponse = {
  id: 'job-999',
  source_id: 'src-1',
  canonical_url: 'https://example.com/job/999',
  company: 'JobScope Labs',
  title: 'Senior Python Engineer',
  description: 'Building high-performance matching systems.',
  responsibilities: 'Write clean code.',
  requirements: [],
  status: 'ACTIVE',
  external_job_id: 'EX-999',
  location: 'Remote',
  work_mode: 'Remote',
  employment_type: 'Full-time',
  salary: '$140k - $170k',
  published_at: '2026-09-01T00:00:00Z',
  first_seen_at: '2026-09-01T00:00:00Z',
  last_seen_at: '2026-09-01T00:00:00Z',
  closed_at: null,
  created_at: '2026-09-01T00:00:00Z',
  updated_at: '2026-09-01T00:00:00Z',
  source_name: 'Test Source',
  ats_type: 'custom',
  source_url: 'https://example.com',
  content_hash: 'hash999',
};

describe('Search Profile Management UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParamsGet = vi.fn(() => null);
  });

  // 1. /search-profiles empty state
  it('1. renders empty state when no search profiles exist', async () => {
    mockListSearchProfiles.mockResolvedValueOnce([]);

    render(<SearchProfilesClient />);

    expect(screen.getByTestId('profiles-loading')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId('empty-search-profiles')).toBeInTheDocument();
    });

    expect(screen.getByText('No search profiles yet')).toBeInTheDocument();
    expect(screen.getByTestId('create-profile-empty-btn')).toBeInTheDocument();
    expect(screen.getByTestId('create-profile-empty-btn')).toHaveAttribute('href', '/search-profiles/new');
  });

  // 2. Create button navigation link
  it('2. header has create search profile button with correct link', async () => {
    mockListSearchProfiles.mockResolvedValueOnce([mockSingleProfile]);

    render(<SearchProfilesClient />);

    await waitFor(() => {
      expect(screen.getByTestId('create-profile-header-btn')).toBeInTheDocument();
    });

    expect(screen.getByTestId('create-profile-header-btn')).toHaveAttribute('href', '/search-profiles/new');
  });

  // 3. Create form render with all fields
  it('3. renders all form fields on create page', () => {
    render(<CreateSearchProfileClient />);

    expect(screen.getByTestId('profile-name-input')).toBeInTheDocument();
    expect(screen.getByTestId('profile-seniority-input')).toBeInTheDocument();
    expect(screen.getByTestId('profile-target-roles-input')).toBeInTheDocument();
    expect(screen.getByTestId('profile-target-skills-input')).toBeInTheDocument();
    expect(screen.getByTestId('profile-locations-input')).toBeInTheDocument();
    expect(screen.getByTestId('profile-industries-input')).toBeInTheDocument();
    expect(screen.getByTestId('profile-salary-min-input')).toBeInTheDocument();
    expect(screen.getByTestId('profile-salary-max-input')).toBeInTheDocument();
    expect(screen.getByTestId('submit-create-profile-btn')).toBeInTheDocument();
  });

  // 4. Required validation
  it('4. displays validation error when submitting with empty name', async () => {
    render(<CreateSearchProfileClient />);

    const submitBtn = screen.getByTestId('submit-create-profile-btn');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Profile name is required/i)).toBeInTheDocument();
    });

    expect(mockCreateSearchProfile).not.toHaveBeenCalled();
  });

  // 5. Whitespace validation
  it('5. displays validation error when submitting with whitespace-only name', async () => {
    render(<CreateSearchProfileClient />);

    const nameInput = screen.getByTestId('profile-name-input');
    fireEvent.change(nameInput, { target: { value: '    ' } });

    const submitBtn = screen.getByTestId('submit-create-profile-btn');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Profile name is required and cannot be whitespace only/i)).toBeInTheDocument();
    });

    expect(mockCreateSearchProfile).not.toHaveBeenCalled();
  });

  // 5b. Min > Max salary validation
  it('5b. displays validation error when minimum salary exceeds maximum salary', async () => {
    render(<CreateSearchProfileClient />);

    fireEvent.change(screen.getByTestId('profile-name-input'), { target: { value: 'Valid Name' } });
    fireEvent.change(screen.getByTestId('profile-salary-min-input'), { target: { value: '200000' } });
    fireEvent.change(screen.getByTestId('profile-salary-max-input'), { target: { value: '100000' } });

    fireEvent.click(screen.getByTestId('submit-create-profile-btn'));

    await waitFor(() => {
      expect(screen.getByText(/Minimum salary cannot exceed maximum salary/i)).toBeInTheDocument();
    });

    expect(mockCreateSearchProfile).not.toHaveBeenCalled();
  });

  // 6. Successful profile creation
  it('6. successfully submits form and redirects to /search-profiles', async () => {
    mockCreateSearchProfile.mockResolvedValueOnce({
      ...mockSingleProfile,
      id: 'new-profile-id',
      name: 'Senior Backend Engineer',
    });

    render(<CreateSearchProfileClient />);

    fireEvent.change(screen.getByTestId('profile-name-input'), { target: { value: 'Senior Backend Engineer' } });
    fireEvent.change(screen.getByTestId('profile-seniority-input'), { target: { value: 'Senior' } });
    fireEvent.change(screen.getByTestId('profile-target-roles-input'), { target: { value: 'Backend Engineer, Cloud Architect' } });
    fireEvent.change(screen.getByTestId('profile-target-skills-input'), { target: { value: 'Python, PostgreSQL, Docker' } });
    fireEvent.change(screen.getByTestId('profile-locations-input'), { target: { value: 'Remote, Zurich' } });
    fireEvent.change(screen.getByTestId('profile-industries-input'), { target: { value: 'Tech, FinTech' } });
    fireEvent.change(screen.getByTestId('profile-salary-min-input'), { target: { value: '120000' } });
    fireEvent.change(screen.getByTestId('profile-salary-max-input'), { target: { value: '160000' } });

    // Select work mode chip
    fireEvent.click(screen.getByTestId('work-mode-toggle-remote'));

    fireEvent.click(screen.getByTestId('submit-create-profile-btn'));

    await waitFor(() => {
      expect(mockCreateSearchProfile).toHaveBeenCalledTimes(1);
    });

    expect(mockCreateSearchProfile).toHaveBeenCalledWith({
      name: 'Senior Backend Engineer',
      seniority: 'Senior',
      target_roles: ['Backend Engineer', 'Cloud Architect'],
      target_skills: ['Python', 'PostgreSQL', 'Docker'],
      locations: ['Remote', 'Zurich'],
      work_modes: ['Remote'],
      industries: ['Tech', 'FinTech'],
      salary_min: 120000,
      salary_max: 160000,
    });

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/search-profiles');
    });
  });

  // 6b. Successful creation with returnUrl
  it('6b. successfully redirects back to returnUrl with new profile selected', async () => {
    mockSearchParamsGet = vi.fn((key: string) => (key === 'returnUrl' ? '/jobs/job-999' : null));
    mockCreateSearchProfile.mockResolvedValueOnce({
      ...mockSingleProfile,
      id: 'sp-new-123',
    });

    render(<CreateSearchProfileClient />);

    fireEvent.change(screen.getByTestId('profile-name-input'), { target: { value: 'My New Profile' } });
    fireEvent.click(screen.getByTestId('submit-create-profile-btn'));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/jobs/job-999?profile=sp-new-123');
    });
  });

  // 7. API 422 error rendering
  it('7. displays backend 422 validation errors properly', async () => {
    mockCreateSearchProfile.mockRejectedValueOnce(
      new ApiError(422, [
        { loc: ['body', 'name'], msg: 'Search profile name cannot be empty or whitespace only' },
      ])
    );

    render(<CreateSearchProfileClient />);

    fireEvent.change(screen.getByTestId('profile-name-input'), { target: { value: 'Valid Temp' } });
    fireEvent.click(screen.getByTestId('submit-create-profile-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('create-profile-api-error')).toBeInTheDocument();
    });

    expect(screen.getByText('Validation Error')).toBeInTheDocument();
    expect(screen.getAllByText(/Search profile name cannot be empty or whitespace only/i).length).toBeGreaterThanOrEqual(1);
  });

  // 8. API 500 / network error rendering
  it('8. displays server/network errors properly', async () => {
    mockCreateSearchProfile.mockRejectedValueOnce(new ApiError(500, 'Internal Server Error'));

    render(<CreateSearchProfileClient />);

    fireEvent.change(screen.getByTestId('profile-name-input'), { target: { value: 'My Profile' } });
    fireEvent.click(screen.getByTestId('submit-create-profile-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('create-profile-api-error')).toBeInTheDocument();
    });

    expect(screen.getByText(/Internal Server Error/i)).toBeInTheDocument();
  });

  // 9. Submit duplicate request prevention
  it('9. disables submit button during request to prevent duplicate submissions', async () => {
    let resolvePromise: (val: any) => void = () => {};
    mockCreateSearchProfile.mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePromise = resolve;
      })
    );

    render(<CreateSearchProfileClient />);

    fireEvent.change(screen.getByTestId('profile-name-input'), { target: { value: 'Async Profile' } });
    const submitBtn = screen.getByTestId('submit-create-profile-btn');

    fireEvent.click(submitBtn);

    // Button should be loading and disabled
    await waitFor(() => {
      expect(submitBtn).toBeDisabled();
      expect(screen.getByText(/Loading\.\.\./i)).toBeInTheDocument();
    });

    // Second click while pending should not invoke mock again
    fireEvent.click(submitBtn);
    expect(mockCreateSearchProfile).toHaveBeenCalledTimes(1);

    // Resolve promise
    resolvePromise(mockSingleProfile);
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/search-profiles');
    });
  });

  // 10. Job Detail MatchPanel integration when no search profiles exist
  it('10. renders Create Search Profile CTA in Job Detail MatchPanel when searchProfiles is empty', async () => {
    mockGetJobById.mockResolvedValueOnce(mockJob);
    mockListSearchProfiles.mockResolvedValueOnce([]);

    render(<JobDetailClient jobId="job-999" />);

    await waitFor(() => {
      expect(screen.getByTestId('job-detail-content')).toBeInTheDocument();
    });

    // Should see "No search profiles available" in dropdown
    const select = screen.getByTestId('search-profile-selector');
    expect(select).toBeDisabled();
    expect(screen.getByText('No search profiles available')).toBeInTheDocument();

    // Should see Create Search Profile CTA button linking to /search-profiles/new
    const createBtn = screen.getByTestId('create-search-profile-btn');
    expect(createBtn).toBeInTheDocument();
    expect(createBtn).toHaveAttribute('href', '/search-profiles/new?returnUrl=/jobs/job-999');

    // Should also see empty state in MatchPanel
    expect(screen.getByTestId('match-panel-empty-profiles')).toBeInTheDocument();
    expect(screen.getByTestId('match-empty-create-profile-btn')).toBeInTheDocument();
  });

  // 11. Profile appears in Job Detail dropdown after creation
  it('11. renders newly created profile in Job Detail dropdown when profiles exist', async () => {
    mockGetJobById.mockResolvedValueOnce(mockJob);
    mockListSearchProfiles.mockResolvedValueOnce([mockSingleProfile]);
    mockGetSavedMatch.mockResolvedValueOnce({
      id: 'match-1',
      job_id: 'job-999',
      base_profile_id: 'bp-1',
      search_profile_id: 'sp-1',
      overall_score: 88,
      deterministic_score: 88,
      final_score: 88,
      confidence: 0.95,
      category_scores: { role: 90, skills: 85 },
      requirement_matches: [],
      explanation: null,
      created_at: null,
      updated_at: null,
    });

    render(<JobDetailClient jobId="job-999" />);

    await waitFor(() => {
      expect(screen.getByTestId('job-detail-content')).toBeInTheDocument();
    });

    // Dropdown contains the profile and is not disabled
    const select = screen.getByTestId('search-profile-selector');
    expect(select).not.toBeDisabled();
    expect(screen.getByText(/Senior Python Engineer \(Senior\)/)).toBeInTheDocument();
  });

  // 12. Search Profiles list delete action
  it('12. allows deleting a profile after user confirmation', async () => {
    mockListSearchProfiles.mockResolvedValueOnce([mockSingleProfile]);
    mockDeleteSearchProfile.mockResolvedValueOnce(undefined);

    render(<SearchProfilesClient />);

    await waitFor(() => {
      expect(screen.getByTestId('profile-card-sp-1')).toBeInTheDocument();
    });

    // Click delete button
    fireEvent.click(screen.getByTestId('delete-profile-btn-sp-1'));

    // Confirmation controls should appear
    expect(screen.getByText('Delete?')).toBeInTheDocument();
    expect(screen.getByTestId('confirm-delete-sp-1')).toBeInTheDocument();

    // Confirm delete
    fireEvent.click(screen.getByTestId('confirm-delete-sp-1'));

    await waitFor(() => {
      expect(mockDeleteSearchProfile).toHaveBeenCalledWith('sp-1');
    });

    // Profile card should now be removed from list
    await waitFor(() => {
      expect(screen.queryByTestId('profile-card-sp-1')).not.toBeInTheDocument();
    });
  });
});
