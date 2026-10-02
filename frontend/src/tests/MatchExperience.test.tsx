import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ScoreGauge } from '../components/matching/ScoreGauge';
import { BlockerAlert } from '../components/matching/BlockerAlert';
import { CategoryScoresBreakdown } from '../components/matching/CategoryScoresBreakdown';
import { SkillsEvidenceList } from '../components/matching/SkillsEvidenceList';
import { RequirementMatchesList } from '../components/matching/RequirementMatchesList';
import { MatchPanel } from '../components/matching/MatchPanel';
import { MatchResultResponse, SearchProfileResponse } from '../lib/api/types';

const mockEvaluateMatch = vi.fn();
const mockGetSavedMatch = vi.fn();
vi.mock('../lib/api/matching', () => ({
  evaluateMatch: (...args: any[]) => mockEvaluateMatch(...args),
  getSavedMatch: (...args: any[]) => mockGetSavedMatch(...args),
}));

const mockProfiles: SearchProfileResponse[] = [
  {
    id: 'p-1',
    base_profile_id: 'bp-1',
    name: 'Backend Profile',
    target_roles: ['Backend Engineer'],
    seniority: 'Senior',
    target_skills: ['Python', 'PostgreSQL'],
    locations: ['Remote'],
    work_modes: ['Remote'],
    industries: ['Tech'],
    salary_min: 100000,
    salary_max: 150000,
    created_at: null,
    updated_at: null,
  },
];

const mockMatchResult: MatchResultResponse = {
  id: 'm-1',
  job_id: 'job-1',
  base_profile_id: 'bp-1',
  search_profile_id: 'p-1',
  overall_score: 87.5,
  deterministic_score: 87.5,
  final_score: 87.5,
  confidence: 92.0,
  category_scores: {
    ROLE: 0.95,
    SKILLS: 0.85,
    EXPERIENCE: 0.9,
    LOCATION_WORK_MODE: 1.0,
    EDUCATION: 0.8,
    OTHER: 0.5,
  },
  requirement_matches: [
    {
      id: 'rm-1',
      requirement_id: 'req-1',
      match_status: 'MATCHED',
      score: 1.0,
      reason: 'Candidate has 8 years of Python experience exceeding 5 years requirement.',
      evidence: 'Worked as Staff Python Engineer at Acme.',
      is_blocker: false,
    },
    {
      id: 'rm-2',
      requirement_id: 'req-2',
      match_status: 'NOT_MATCHED',
      score: 0.0,
      reason: 'Role requires Swiss work authorization.',
      evidence: null,
      is_blocker: true,
    },
  ],
  explanation: {
    summary: 'Strong technical fit with work authorization blocker.',
    matched_skills: ['Python', 'PostgreSQL', 'Docker'],
    partial_matches: ['Kubernetes'],
    missing_skills: ['Rust'],
    role_result: 'MATCHED',
    experience_result: 'MATCHED',
    education_result: 'MATCHED',
    location_result: 'NOT_MATCHED',
    blockers: ['Requires Swiss work authorization'],
    unknowns: [],
    category_explanations: {},
  },
  created_at: '2026-09-29T10:00:00Z',
  updated_at: '2026-09-29T10:00:00Z',
};

describe('Match Experience Components', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('ScoreGauge', () => {
    it('renders overall score and confidence correctly', () => {
      render(<ScoreGauge overallScore={87.5} confidence={92.0} />);

      expect(screen.getByText('88')).toBeInTheDocument();
      expect(screen.getByText('92%')).toBeInTheDocument();
      expect(screen.getByText('Strong Alignment')).toBeInTheDocument();

      const gauge = screen.getByTestId('score-gauge');
      expect(gauge.querySelector('.score-high')).toBeInTheDocument();
    });

    it('applies correct semantic styles for moderate and low scores', () => {
      const { rerender } = render(<ScoreGauge overallScore={65.0} confidence={80.0} />);
      expect(screen.getByText('65')).toBeInTheDocument();
      expect(screen.getByText('Moderate Fit')).toBeInTheDocument();

      rerender(<ScoreGauge overallScore={40.0} confidence={50.0} />);
      expect(screen.getByText('40')).toBeInTheDocument();
      expect(screen.getByText('Low Alignment')).toBeInTheDocument();
    });
  });

  describe('BlockerAlert', () => {
    it('renders blocker warning when blockers exist', () => {
      render(<BlockerAlert blockers={['Requires Swiss work authorization', 'Missing clearance']} />);

      expect(screen.getByText(/Hard Blocker Disqualification Detected/i)).toBeInTheDocument();
      expect(screen.getByText('Requires Swiss work authorization')).toBeInTheDocument();
      expect(screen.getByText('Missing clearance')).toBeInTheDocument();
    });

    it('renders nothing when blockers array is empty', () => {
      const { container } = render(<BlockerAlert blockers={[]} />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe('CategoryScoresBreakdown', () => {
    it('renders all standard categories with progress bars', () => {
      render(<CategoryScoresBreakdown categoryScores={mockMatchResult.category_scores} />);

      expect(screen.getByText('Role & Title Alignment')).toBeInTheDocument();
      expect(screen.getByText('Technical & Required Skills')).toBeInTheDocument();
      expect(screen.getByText('Years of Experience & Seniority')).toBeInTheDocument();
      expect(screen.getByText('Location & Work Mode Fit')).toBeInTheDocument();
      expect(screen.getByText('Education & Degree Level')).toBeInTheDocument();

      expect(screen.getByText('95%')).toBeInTheDocument();
      expect(screen.getByText('85%')).toBeInTheDocument();
      expect(screen.getByText('100%')).toBeInTheDocument();
    });
  });

  describe('SkillsEvidenceList', () => {
    it('renders matched, partial, and missing skills chips', () => {
      render(<SkillsEvidenceList explanation={mockMatchResult.explanation} />);

      expect(screen.getByText('✓ Python')).toBeInTheDocument();
      expect(screen.getByText('✓ PostgreSQL')).toBeInTheDocument();
      expect(screen.getByText('~ Kubernetes')).toBeInTheDocument();
      expect(screen.getByText('✕ Rust')).toBeInTheDocument();
    });
  });

  describe('RequirementMatchesList', () => {
    it('renders requirement status, reasons, evidence, and blocker tags', () => {
      render(<RequirementMatchesList requirements={mockMatchResult.requirement_matches} />);

      expect(screen.getByText('Matched')).toBeInTheDocument();
      expect(screen.getByText('Not Matched')).toBeInTheDocument();
      expect(screen.getByText('Mandatory Blocker')).toBeInTheDocument();
      expect(screen.getByText(/Candidate has 8 years of Python experience/)).toBeInTheDocument();
      expect(screen.getByText('Worked as Staff Python Engineer at Acme.')).toBeInTheDocument();
    });
  });

  describe('MatchPanel Component', () => {
    it('retrieves saved match on mount and displays results without calculation', async () => {
      mockGetSavedMatch.mockResolvedValue(mockMatchResult);

      render(
        <MatchPanel
          jobId="job-1"
          searchProfiles={mockProfiles}
          selectedProfileId="p-1"
          onSelectProfile={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(mockGetSavedMatch).toHaveBeenCalledWith(
          'job-1', 'p-1',
          expect.any(AbortSignal)
        );
      });

      await waitFor(() => {
        expect(screen.getByText('88')).toBeInTheDocument();
        expect(screen.getByText(/Hard Blocker Disqualification Detected/i)).toBeInTheDocument();
        expect(screen.getByText('Technical & Required Skills')).toBeInTheDocument();
      });
      expect(mockEvaluateMatch).not.toHaveBeenCalled();
    });

    it('triggers re-evaluation when re-evaluate button is clicked', async () => {
      mockEvaluateMatch.mockResolvedValue(mockMatchResult);
      mockGetSavedMatch.mockResolvedValue(mockMatchResult);

      render(
        <MatchPanel
          jobId="job-1"
          searchProfiles={mockProfiles}
          selectedProfileId="p-1"
          onSelectProfile={vi.fn()}
          initialMatchResult={mockMatchResult}
        />
      );

      expect(screen.getByText('88')).toBeInTheDocument();

      const reEvalBtn = screen.getByTestId('re-evaluate-btn');
      await waitFor(() => expect(reEvalBtn).not.toBeDisabled());
      fireEvent.click(reEvalBtn);

      await waitFor(() => {
        expect(mockEvaluateMatch).toHaveBeenCalledTimes(1);
      });
    });
  });
});
