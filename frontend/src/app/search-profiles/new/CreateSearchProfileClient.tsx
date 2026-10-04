'use client';

import React, { useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { createSearchProfile, updateSearchProfile } from '@/lib/api/search_profiles';
import { ApiError, ApiErrorDetail, SearchProfileCreateRequest, SearchProfileResponse } from '@/lib/api/types';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';

const SENIORITY_PRESETS = ['Junior', 'Mid-Level', 'Senior', 'Lead', 'Staff', 'Principal'];
const COMMON_WORK_MODES = ['Remote', 'Hybrid', 'On-site'];

function parseCommaList(input: string): string[] {
  return input
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

export function CreateSearchProfileClient({initialProfile, onSaved, onCancel}: {
  initialProfile?: SearchProfileResponse;
  onSaved?: (profile: SearchProfileResponse) => void;
  onCancel?: () => void;
} = {}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnUrl = initialProfile ? null : searchParams.get('returnUrl');
  const submitLock = useRef(false);
  const editorList = (text: string, field: 'target_roles' | 'target_skills' | 'locations' | 'industries') =>
    initialProfile && text === initialProfile[field].join(', ') ? initialProfile[field] : parseCommaList(text);

  // Form State
  const [name, setName] = useState(initialProfile?.name ?? '');
  const [seniority, setSeniority] = useState(initialProfile?.seniority ?? '');
  const [targetRolesText, setTargetRolesText] = useState(initialProfile?.target_roles.join(', ') ?? '');
  const [targetSkillsText, setTargetSkillsText] = useState(initialProfile?.target_skills.join(', ') ?? '');
  const [selectedWorkModes, setSelectedWorkModes] = useState<string[]>(initialProfile?.work_modes ?? []);
  const [locationsText, setLocationsText] = useState(initialProfile?.locations.join(', ') ?? '');
  const [industriesText, setIndustriesText] = useState(initialProfile?.industries.join(', ') ?? '');
  const [salaryMin, setSalaryMin] = useState(String(initialProfile?.salary_min ?? ''));
  const [salaryMax, setSalaryMax] = useState(String(initialProfile?.salary_max ?? ''));

  // UI / Submission State
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<{
    status: number;
    message: string;
    details?: string | ApiErrorDetail[];
  } | null>(null);

  const toggleWorkMode = (mode: string) => {
    setSelectedWorkModes((prev) =>
      prev.includes(mode) ? prev.filter((m) => m !== mode) : [...prev, mode]
    );
  };

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    // Name validation
    if (!name.trim()) {
      errors.name = 'Profile name is required and cannot be whitespace only.';
    } else if (name.length > 150) {
      errors.name = 'Profile name cannot exceed 150 characters.';
    }

    // Seniority validation
    if (seniority.length > 50) {
      errors.seniority = 'Seniority cannot exceed 50 characters.';
    }

    // Salary validation
    const minNum = salaryMin.trim() !== '' ? Number(salaryMin) : null;
    const maxNum = salaryMax.trim() !== '' ? Number(salaryMax) : null;

    if (minNum !== null) {
      if (isNaN(minNum) || minNum < 0) {
        errors.salary_min = 'Minimum salary must be a non-negative number.';
      } else if (minNum > 9999999999.99) {
        errors.salary_min = 'Minimum salary exceeds allowable maximum value.';
      }
    }

    if (maxNum !== null) {
      if (isNaN(maxNum) || maxNum < 0) {
        errors.salary_max = 'Maximum salary must be a non-negative number.';
      } else if (maxNum > 9999999999.99) {
        errors.salary_max = 'Maximum salary exceeds allowable maximum value.';
      }
    }

    if (minNum !== null && maxNum !== null && !isNaN(minNum) && !isNaN(maxNum)) {
      if (minNum > maxNum) {
        errors.salary_max = 'Minimum salary cannot exceed maximum salary.';
      }
    }

    // List validation checks
    const roles = editorList(targetRolesText, 'target_roles');
    if (roles.length > 50) {
      errors.target_roles = 'Cannot exceed 50 target roles.';
    } else if (roles.some((r) => r.length > 150)) {
      errors.target_roles = 'Individual role names cannot exceed 150 characters.';
    }

    const skills = editorList(targetSkillsText, 'target_skills');
    if (skills.length > 50) {
      errors.target_skills = 'Cannot exceed 50 target skills.';
    } else if (skills.some((s) => s.length > 150)) {
      errors.target_skills = 'Individual skill names cannot exceed 150 characters.';
    }

    const locs = editorList(locationsText, 'locations');
    if (locs.length > 50) {
      errors.locations = 'Cannot exceed 50 locations.';
    } else if (locs.some((l) => l.length > 150)) {
      errors.locations = 'Individual location names cannot exceed 150 characters.';
    }

    const inds = editorList(industriesText, 'industries');
    if (inds.length > 50) {
      errors.industries = 'Cannot exceed 50 industries.';
    } else if (inds.some((i) => i.length > 150)) {
      errors.industries = 'Individual industry names cannot exceed 150 characters.';
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Prevent duplicate request when already submitting
    if (submitLock.current) return;

    setApiError(null);
    if (!validateForm()) return;

    submitLock.current = true;
    setIsSubmitting(true);

    const minNum = salaryMin.trim() !== '' ? Number(salaryMin) : null;
    const maxNum = salaryMax.trim() !== '' ? Number(salaryMax) : null;

    const payload: SearchProfileCreateRequest = {
      name: name.trim(),
      seniority: seniority.trim() || null,
      target_roles: editorList(targetRolesText, 'target_roles'),
      target_skills: editorList(targetSkillsText, 'target_skills'),
      locations: editorList(locationsText, 'locations'),
      work_modes: selectedWorkModes,
      industries: editorList(industriesText, 'industries'),
      salary_min: minNum,
      salary_max: maxNum,
    };

    try {
      if (initialProfile) {
        const updated = await updateSearchProfile(initialProfile.id, payload);
        onSaved?.(updated);
        return;
      }
      const created = await createSearchProfile(payload);

      // Successfully created profile!
      if (returnUrl) {
        // Return user to original job detail view with the newly created profile selected
        const parsedUrl = new URL(returnUrl, window.location.origin);
        parsedUrl.searchParams.set('profile', created.id);
        router.push(parsedUrl.pathname + parsedUrl.search);
      } else {
        router.push('/search-profiles');
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.isValidationError && Array.isArray(err.detail)) {
          const backendFieldErrors: Record<string, string> = {};
          for (const item of err.detail) {
            if (item.loc && item.loc.length > 0) {
              const fieldName = String(item.loc[item.loc.length - 1]);
              if (item.msg) {
                backendFieldErrors[fieldName] = item.msg;
              }
            }
          }
          setFieldErrors((prev) => ({ ...prev, ...backendFieldErrors }));
        }

        setApiError({
          status: err.status,
          message: err.message,
          details: err.detail,
        });
      } else {
        setApiError({
          status: 500,
          message: err instanceof Error ? err.message : 'An unexpected network error occurred.',
        });
      }
    } finally {
      submitLock.current = false;
      setIsSubmitting(false);
    }
  };

  const cancelDestination = returnUrl || '/search-profiles';

  return (
    <div className="container" style={{ paddingTop: '2rem', paddingBottom: '4rem', maxWidth: '720px' }}>
      {/* Back Link */}
      <div style={{ marginBottom: '1.5rem' }}>
        {initialProfile ? <Button type="button" variant="secondary" disabled={isSubmitting} onClick={onCancel}>Back to Search Profiles</Button> : <Link
          href={cancelDestination}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.4rem',
            color: 'var(--text-secondary)',
            fontSize: '0.875rem',
            textDecoration: 'none',
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          <span>{returnUrl ? 'Back to Job Detail' : 'Back to Search Profiles'}</span>
        </Link>}
      </div>

      <Card style={{ padding: '2rem' }}>
        <div style={{ marginBottom: '2rem' }}>
          <h1
            style={{
              fontSize: '1.5rem',
              fontWeight: 700,
              color: 'var(--text-primary)',
              letterSpacing: '-0.02em',
            }}
          >
            {initialProfile ? 'Edit Search Profile' : 'Create Search Profile'}
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
            Set candidate target criteria, skills, and work preferences for deterministic match evaluation.
          </p>
        </div>

        {/* Global API Error Alert */}
        {apiError && (
          <div style={{ marginBottom: '1.5rem' }} data-testid="create-profile-api-error">
            <Alert
              variant="danger"
              title={
                apiError.status === 401
                  ? 'Authentication Required'
                  : apiError.status === 422
                    ? 'Validation Error'
                    : apiError.status >= 500
                      ? 'Server Error'
                      : 'Request Failed'
              }
            >
              {apiError.message}
            </Alert>
          </div>
        )}

        <form aria-label={initialProfile ? 'Edit Search Profile' : 'Create Search Profile'} onSubmit={handleSubmit} noValidate style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <fieldset disabled={isSubmitting} style={{border: 0, padding: 0, margin: 0, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
          {/* Profile Name (Required) */}
          <div>
            <Input
              label="Profile Name *"
              id="search-profile-name"
              name="name"
              placeholder="e.g. Senior Backend Engineer"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (fieldErrors.name) {
                  setFieldErrors((prev) => ({ ...prev, name: '' }));
                }
              }}
              error={fieldErrors.name}
              required
              aria-required="true"
              data-testid="profile-name-input"
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
              A descriptive title for your candidate search profile (required, max 150 characters).
            </span>
          </div>

          {/* Seniority */}
          <div>
            <Input
              label="Seniority Level"
              id="search-profile-seniority"
              name="seniority"
              placeholder="e.g. Senior"
              value={seniority}
              onChange={(e) => {
                setSeniority(e.target.value);
                if (fieldErrors.seniority) {
                  setFieldErrors((prev) => ({ ...prev, seniority: '' }));
                }
              }}
              error={fieldErrors.seniority}
              data-testid="profile-seniority-input"
            />
            <p className="text-muted" style={{fontSize: '0.75rem', marginTop: '0.25rem'}}>One seniority level per profile (optional).</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem', marginTop: '0.5rem' }}>
              {SENIORITY_PRESETS.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setSeniority(preset)}
                  aria-pressed={seniority === preset}
                  style={{
                    fontSize: '0.75rem',
                    padding: '0.2rem 0.5rem',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    backgroundColor: seniority === preset ? 'var(--primary)' : 'rgba(255, 255, 255, 0.04)',
                    color: seniority === preset ? '#ffffff' : 'var(--text-secondary)',
                    cursor: 'pointer',
                  }}
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>

          {/* Target Roles */}
          <div>
            <Input
              label="Target Roles"
              id="search-profile-target-roles"
              name="target_roles"
              placeholder="e.g. Backend Engineer, Software Architect, Python Developer"
              value={targetRolesText}
              onChange={(e) => {
                setTargetRolesText(e.target.value);
                if (fieldErrors.target_roles) {
                  setFieldErrors((prev) => ({ ...prev, target_roles: '' }));
                }
              }}
              error={fieldErrors.target_roles}
              data-testid="profile-target-roles-input"
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
              Comma-separated target titles (up to 50 items, max 150 chars each).
            </span>
          </div>

          {/* Target Skills */}
          <div>
            <Input
              label="Target Skills"
              id="search-profile-target-skills"
              name="target_skills"
              placeholder="e.g. Python, PostgreSQL, Docker, FastAPI, AWS"
              value={targetSkillsText}
              onChange={(e) => {
                setTargetSkillsText(e.target.value);
                if (fieldErrors.target_skills) {
                  setFieldErrors((prev) => ({ ...prev, target_skills: '' }));
                }
              }}
              error={fieldErrors.target_skills}
              data-testid="profile-target-skills-input"
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
              Comma-separated candidate skills evaluated against job requirements.
            </span>
          </div>

          {/* Work Modes */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-secondary)' }}>
              Preferred Work Modes
            </span>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              {COMMON_WORK_MODES.map((mode) => {
                const isSelected = selectedWorkModes.includes(mode);
                return (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => toggleWorkMode(mode)}
                    data-testid={`work-mode-toggle-${mode.toLowerCase()}`}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                      fontSize: '0.8125rem',
                      padding: '0.4rem 0.85rem',
                      borderRadius: 'var(--radius-full)',
                      border: `1px solid ${isSelected ? 'var(--primary)' : 'var(--border-card)'}`,
                      backgroundColor: isSelected ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                      color: isSelected ? 'var(--primary-light)' : 'var(--text-secondary)',
                      cursor: 'pointer',
                      transition: 'all var(--transition-fast)',
                    }}
                  >
                    <span>{isSelected ? '✓' : '+'}</span>
                    <span>{mode}</span>
                  </button>
                );
              })}
            </div>
            {fieldErrors.work_modes && (
              <span role="alert" style={{ fontSize: '0.75rem', color: 'var(--danger-text)' }}>
                {fieldErrors.work_modes}
              </span>
            )}
          </div>

          {/* Locations */}
          <div>
            <Input
              label="Target Locations"
              id="search-profile-locations"
              name="locations"
              placeholder="e.g. Remote, Istanbul, London, Berlin"
              value={locationsText}
              onChange={(e) => {
                setLocationsText(e.target.value);
                if (fieldErrors.locations) {
                  setFieldErrors((prev) => ({ ...prev, locations: '' }));
                }
              }}
              error={fieldErrors.locations}
              data-testid="profile-locations-input"
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
              Comma-separated target cities, countries, or regions.
            </span>
          </div>

          {/* Industries */}
          <div>
            <Input
              label="Target Industries"
              id="search-profile-industries"
              name="industries"
              placeholder="e.g. FinTech, SaaS, Gaming, E-Commerce"
              value={industriesText}
              onChange={(e) => {
                setIndustriesText(e.target.value);
                if (fieldErrors.industries) {
                  setFieldErrors((prev) => ({ ...prev, industries: '' }));
                }
              }}
              error={fieldErrors.industries}
              data-testid="profile-industries-input"
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
              Comma-separated industry sectors.
            </span>
          </div>

          {/* Compensation: Salary Min & Max */}
          <div>
            <span style={{ fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.5rem' }}>
              Desired Salary Range (Annual)
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <Input
                label="Minimum Salary"
                id="search-profile-salary-min"
                name="salary_min"
                type="number"
                min="0"
                step="1000"
                placeholder="e.g. 100000"
                value={salaryMin}
                onChange={(e) => {
                  setSalaryMin(e.target.value);
                  if (fieldErrors.salary_min) {
                    setFieldErrors((prev) => ({ ...prev, salary_min: '' }));
                  }
                }}
                error={fieldErrors.salary_min}
                data-testid="profile-salary-min-input"
              />
              <Input
                label="Maximum Salary"
                id="search-profile-salary-max"
                name="salary_max"
                type="number"
                min="0"
                step="1000"
                placeholder="e.g. 150000"
                value={salaryMax}
                onChange={(e) => {
                  setSalaryMax(e.target.value);
                  if (fieldErrors.salary_max) {
                    setFieldErrors((prev) => ({ ...prev, salary_max: '' }));
                  }
                }}
                error={fieldErrors.salary_max}
                data-testid="profile-salary-max-input"
              />
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
              Values must be non-negative. Enter annual compensation figures.
            </span>
          </div>

          {/* Submit Actions */}
          </fieldset>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              gap: '1rem',
              marginTop: '1rem',
              paddingTop: '1.5rem',
              borderTop: '1px solid var(--border-subtle)',
            }}
          >
            {initialProfile ? <Button type="button" variant="secondary" disabled={isSubmitting} onClick={onCancel}>Cancel</Button> : <Link
              href={cancelDestination}
              className="btn btn-secondary"
              style={{ textDecoration: 'none' }}
              data-testid="cancel-create-profile-btn"
            >
              Cancel
            </Link>}

            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              disabled={isSubmitting}
              data-testid="submit-create-profile-btn"
            >
              {initialProfile ? 'Save Changes' : 'Create Search Profile'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
