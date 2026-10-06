/**
 * API Type Definitions for JobScope Frontend.
 *
 * Mapped strictly to backend Pydantic schemas in:
 * - backend/interfaces/api/schemas/job.py
 * - backend/interfaces/api/schemas/search_profile.py
 * - backend/interfaces/api/schemas/matching.py
 */

export interface JobSummaryResponse {
  id: string;
  source_id: string;
  canonical_url: string;
  company: string;
  title: string;
  status: 'ACTIVE' | 'CLOSED' | string;
  external_job_id: string | null;
  location: string | null;
  work_mode: string | null;
  employment_type: string | null;
  salary: string | null;
  published_at: string | null;
  first_seen_at: string | null;
  last_seen_at: string | null;
  closed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  source_name: string | null;
  ats_type: string | null;
  source_url: string | null;
}

export interface JobDetailResponse extends JobSummaryResponse {
  occurrences?: { id: string; source_id: string; source: string; ats_type: string; external_job_id: string | null; url: string; status: string; first_seen_at: string; last_seen_at: string }[];
  description: string;
  content_hash: string;
  responsibilities: string | null;
  requirements?: Record<string, any>[];
}

export interface JobListResponse {
  jobs: JobSummaryResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface JobFilterParams {
  status?: string;
  source_id?: string;
  ats_type?: string;
  company?: string;
  location?: string;
  work_mode?: string;
  employment_type?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

export interface SearchProfileResponse {
  id: string;
  base_profile_id: string;
  name: string;
  target_roles: string[];
  seniority: string | null;
  target_skills: string[];
  locations: string[];
  work_modes: string[];
  industries: string[];
  salary_min: number | null;
  salary_max: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface SearchProfileCreateRequest {
  name: string;
  target_roles?: string[];
  seniority?: string | null;
  target_skills?: string[];
  locations?: string[];
  work_modes?: string[];
  industries?: string[];
  salary_min?: number | null;
  salary_max?: number | null;
}

export interface MatchRequest {
  job_id: string;
  search_profile_id: string;
}

export type MatchStatus = 'MATCHED' | 'PARTIAL' | 'NOT_MATCHED' | 'UNKNOWN';

export type ApplicationStatus = 'INTERESTED' | 'APPLYING' | 'APPLIED' | 'INTERVIEW' | 'OFFER' | 'REJECTED';
export interface ApplicationHistory {
  id: string; application_id: string; from_status: ApplicationStatus;
  to_status: ApplicationStatus; changed_at: string | null;
}
export interface Application {
  id: string; job_id: string; user_id: string; status: ApplicationStatus;
  notes: string | null; created_at: string | null; updated_at: string | null;
  job: {id: string; canonical_url: string; company: string; title: string; status: string;
    location: string | null; work_mode: string | null; employment_type: string | null;
    salary: string | null; source_name: string | null} | null;
  status_history: ApplicationHistory[];
}
export interface ApplicationListResponse {
  items: Application[]; total: number; limit: number; offset: number;
}

export interface RequirementMatchResponse {
  id: string;
  requirement_id: string;
  match_status: MatchStatus;
  score: number;
  reason: string;
  evidence: string | null;
  is_blocker: boolean;
}

export interface CategoryExplanationResponse {
  category: string;
  status: string;
  score: number;
  reason: string;
  details: string[];
}

export interface MatchExplanationResponse {
  summary: string;
  matched_skills: string[];
  missing_skills: string[];
  partial_matches: string[];
  role_result: string;
  experience_result: string;
  education_result: string;
  location_result: string;
  blockers: string[];
  unknowns: string[];
  category_explanations: Record<string, CategoryExplanationResponse>;
}

export interface MatchResultResponse {
  id: string;
  job_id: string;
  base_profile_id: string;
  search_profile_id: string;
  overall_score: number;
  deterministic_score: number;
  ai_score?: number | string | null;
  ai_adjustment?: number | string | null;
  ai_analysis?: AIAnalysisResponse | null;
  final_score: number;
  confidence: number;
  category_scores: Record<string, number>;
  requirement_matches: RequirementMatchResponse[];
  explanation: MatchExplanationResponse | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AIAnalysisResponse {
  id: string; match_result_id: string; provider: string; model: string;
  ai_score: number | string; assessment: string; summary: string;
  strengths: string[]; gaps: string[]; risks: string[];
  evidence: {id: string; claim: string; evidence_type: string; source_reference: string; source_quote: string | null; reason: string}[];
  created_at: string | null; cached: boolean;
}

export interface ApiErrorDetail {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string | ApiErrorDetail[],
    public code?: string,
  ) {
    const formattedMessage =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
          : JSON.stringify(detail);
    super(formattedMessage);
    this.name = 'ApiError';
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isValidationError(): boolean {
    return this.status === 422;
  }

  get isServerError(): boolean {
    return this.status >= 500;
  }
}
