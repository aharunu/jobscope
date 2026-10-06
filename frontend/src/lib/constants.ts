/**
 * Application Constants and Filter Definitions.
 */

export const WORK_MODE_OPTIONS = [
  { value: '', label: 'All Work Modes' },
  { value: 'Remote', label: 'Remote' },
  { value: 'Hybrid', label: 'Hybrid' },
  { value: 'On-site', label: 'On-site' },
] as const;

export const EMPLOYMENT_TYPE_OPTIONS = [
  { value: '', label: 'All Employment Types' },
  { value: 'Full-time', label: 'Full-time' },
  { value: 'Part-time', label: 'Part-time' },
  { value: 'Contract', label: 'Contract' },
  { value: 'Internship', label: 'Internship' },
] as const;

export const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'ACTIVE', label: 'Active' },
  { value: 'CLOSED', label: 'Closed' },
] as const;

export const ATS_TYPE_OPTIONS = [
  { value: '', label: 'All Platforms' },
  { value: 'lever', label: 'Lever' },
  { value: 'greenhouse', label: 'Greenhouse' },
  { value: 'ashby', label: 'Ashby' },
  { value: 'workday', label: 'Workday' },
  { value: 'smartrecruiters', label: 'SmartRecruiters' },
  { value: 'recruitee', label: 'Recruitee' },
  { value: 'personio', label: 'Personio' },
  { value: 'teamtailor', label: 'Teamtailor' },
  { value: 'workable', label: 'Workable' },
  { value: 'hirex', label: 'Hirex' },
  { value: 'bamboohr', label: 'BambooHR' },
  { value: 'oracle', label: 'Oracle' },
] as const;

export const DEFAULT_PAGE_SIZE = 50;
export const PAGE_SIZE_OPTIONS = [25, 50, 100] as const;
