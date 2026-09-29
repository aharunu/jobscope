import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SearchProfileSelector } from '../components/search_profile/SearchProfileSelector';
import { SearchProfileResponse } from '../lib/api/types';

const mockProfiles: SearchProfileResponse[] = [
  {
    id: 'p-1',
    base_profile_id: 'bp-1',
    name: 'Senior Backend Engineer',
    target_roles: ['Backend Engineer'],
    seniority: 'Senior',
    target_skills: ['Python', 'PostgreSQL'],
    locations: ['Remote'],
    work_modes: ['Remote'],
    industries: ['FinTech'],
    salary_min: 120000,
    salary_max: 160000,
    created_at: null,
    updated_at: null,
  },
  {
    id: 'p-2',
    base_profile_id: 'bp-1',
    name: 'Staff Architect',
    target_roles: ['Architect'],
    seniority: 'Staff',
    target_skills: ['Distributed Systems', 'Cloud'],
    locations: ['Remote', 'Zurich'],
    work_modes: ['Hybrid'],
    industries: ['Tech'],
    salary_min: 180000,
    salary_max: 240000,
    created_at: null,
    updated_at: null,
  },
];

describe('SearchProfileSelector Component', () => {
  it('renders all profile options in dropdown', () => {
    const handleSelect = vi.fn();
    render(
      <SearchProfileSelector
        profiles={mockProfiles}
        selectedProfileId="p-1"
        onSelectProfile={handleSelect}
      />
    );

    const select = screen.getByTestId('search-profile-selector');
    expect(select).toBeInTheDocument();
    expect(select).toHaveValue('p-1');
    expect(screen.getByText(/Senior Backend Engineer/)).toBeInTheDocument();
    expect(screen.getByText(/Staff Architect/)).toBeInTheDocument();
  });

  it('triggers onSelectProfile when a different profile is selected', () => {
    const handleSelect = vi.fn();
    render(
      <SearchProfileSelector
        profiles={mockProfiles}
        selectedProfileId="p-1"
        onSelectProfile={handleSelect}
      />
    );

    const select = screen.getByTestId('search-profile-selector');
    fireEvent.change(select, { target: { value: 'p-2' } });

    expect(handleSelect).toHaveBeenCalledWith('p-2');
  });

  it('renders disabled state when disabled prop is true', () => {
    const handleSelect = vi.fn();
    render(
      <SearchProfileSelector
        profiles={mockProfiles}
        selectedProfileId="p-1"
        onSelectProfile={handleSelect}
        disabled={true}
      />
    );

    const select = screen.getByTestId('search-profile-selector');
    expect(select).toBeDisabled();
  });

  it('renders empty fallback when no profiles exist', () => {
    const handleSelect = vi.fn();
    render(
      <SearchProfileSelector
        profiles={[]}
        selectedProfileId=""
        onSelectProfile={handleSelect}
      />
    );

    const select = screen.getByTestId('search-profile-selector');
    expect(select).toBeDisabled();
    expect(screen.getByText('No search profiles available')).toBeInTheDocument();
  });
});
