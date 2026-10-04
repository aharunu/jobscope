import React from 'react';
import {render, screen, fireEvent, waitFor, within} from '@testing-library/react';
import {beforeEach, describe, expect, it, vi} from 'vitest';
import ProfileClient from '../app/profile/ProfileClient';
import {ApiError} from '../lib/api/types';

const api = vi.hoisted(() => ({getProfile: vi.fn(), getSkillSuggestions: vi.fn(), updateProfile: vi.fn(), saveProfileEntry: vi.fn(), deleteProfileEntry: vi.fn()}));
vi.mock('../lib/api/profile', () => api);
const blank = {id: 'base', name: 'Candidate Profile', summary: null, skills: [], experiences: [], educations: [], projects: []};
const change = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), {target: {value}});

describe('Manual candidate profile', () => {
  beforeEach(() => {vi.resetAllMocks(); api.getProfile.mockResolvedValue(blank); api.getSkillSuggestions.mockResolvedValue([]); vi.spyOn(window, 'confirm').mockReturnValue(true);});
  it('shows loading, creates the blank profile through PATCH and prevents duplicate saves', async () => {
    let resolve!: (value: unknown) => void;
    api.updateProfile.mockImplementation(() => new Promise(r => {resolve = r;}));
    render(<ProfileClient/>);
    expect(screen.getByText('Loading profile...')).toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', {name: 'Create Profile'}));
    change('Profile name', ' Ada '); change('Summary', ' Python engineer ');
    const form = screen.getByRole('form', {name: 'Profile editor'});
    fireEvent.submit(form); fireEvent.submit(form);
    expect(api.updateProfile).toHaveBeenCalledTimes(1);
    expect(api.updateProfile).toHaveBeenCalledWith({name: 'Ada', summary: 'Python engineer'});
    expect(screen.getByRole('button', {name: 'Saving...'})).toBeDisabled();
    resolve({...blank, name: 'Ada', summary: 'Python engineer'});
    expect(await screen.findByText('Profile saved.')).toBeInTheDocument();
    expect(screen.getByRole('heading', {name: 'Ada'})).toBeInTheDocument();
  });
  it('handles missing profile, load failure/retry and keeps a failed save draft', async () => {
    api.getProfile.mockRejectedValueOnce(new Error('Offline')).mockRejectedValueOnce(new ApiError(404, 'Missing')).mockResolvedValue(blank);
    api.updateProfile.mockRejectedValue(new Error('Save unavailable'));
    render(<ProfileClient/>);
    expect(await screen.findByText('Offline')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', {name: 'Retry Profile'}));
    fireEvent.click(await screen.findByRole('button', {name: 'Create Profile'}));
    fireEvent.submit(screen.getByRole('form', {name: 'Profile editor'}));
    expect(await screen.findByText('Profile name is required.')).toBeInTheDocument();
    expect(api.updateProfile).not.toHaveBeenCalled();
    change('Profile name', 'Ada');
    fireEvent.submit(screen.getByRole('form', {name: 'Profile editor'}));
    expect(await screen.findByText('Save unavailable')).toBeInTheDocument();
    expect(screen.getByLabelText('Profile name')).toHaveValue('Ada');
    expect(api.getProfile).toHaveBeenCalledTimes(3);
  });
  it('loads and edits existing summary without discarding children', async () => {
    api.getProfile.mockResolvedValue({...blank, name: 'Ada', summary: 'Old', skills: [{id: 'skill', name: 'Python', category: null, years_of_experience: 5, level: 'Senior'}]});
    api.updateProfile.mockResolvedValue({...blank, name: 'Ada', summary: 'New'});
    render(<ProfileClient/>);
    fireEvent.click(await screen.findByRole('button', {name: 'Edit Profile'}));
    expect(screen.getByLabelText('Summary')).toHaveValue('Old'); change('Summary', 'New');
    fireEvent.submit(screen.getByRole('form', {name: 'Profile editor'}));
    await screen.findByText('Profile saved.');
    expect(screen.getByText('Python')).toBeInTheDocument();
  });
  it.each([
    ['skills', 'Skill', 'Skills', {'Skill name': 'Python', 'Years of experience': '4.5', Level: 'ADVANCED'}, {name: 'Python', category: null, years_of_experience: 4.5, level: 'ADVANCED'}],
    ['experiences', 'Experience', 'Experience', {Company: 'Acme', 'Role title': 'Engineer', 'Start date': '2020-01-01', 'End date': '2022-01-01', Description: 'Built services', 'Skills used (one per line)': 'Python\n SQL '}, {company: 'Acme', title: 'Engineer', start_date: '2020-01-01', end_date: '2022-01-01', is_current: false, description: 'Built services', skills_used: ['Python', 'SQL']}],
    ['educations', 'Education', 'Education', {School: 'University', Degree: 'BSc', 'Field of study': 'Computing', 'Start year': '2015', 'End year': '2019'}, {school: 'University', degree: 'BSc', field_of_study: 'Computing', start_year: 2015, end_year: 2019}],
    ['projects', 'Project', 'Projects', {'Project title': 'JobScope', Description: 'Portfolio', 'Skills used (one per line)': 'Python\n SQL', 'Project URL': 'https://example.org'}, {title: 'JobScope', description: 'Portfolio', skills_used: ['Python', 'SQL'], url: 'https://example.org'}],
  ] as const)('adds, edits and removes %s using the actual API fields', async (section, singular, region, fields, payload) => {
    api.saveProfileEntry.mockResolvedValue({id: 'entry', base_profile_id: 'base', ...payload});
    render(<ProfileClient/>);
    fireEvent.click(await screen.findByRole('button', {name: `Add ${singular}`}));
    Object.entries(fields).forEach(([label, value]) => change(label, value));
    fireEvent.submit(screen.getByRole('form', {name: `${singular} editor`}));
    await screen.findByText(`${singular} saved.`);
    expect(api.saveProfileEntry).toHaveBeenCalledWith(section, payload, undefined);
    const scoped = within(screen.getByRole('region', {name: region}));
    fireEvent.click(scoped.getByRole('button', {name: `Edit ${singular}`}));
    Object.entries(fields).forEach(([label, value]) => expect(screen.getByLabelText(label)).toHaveValue(value === '4.5' ? 4.5 : ['2015', '2019'].includes(value) ? Number(value) : value.includes('\n') ? 'Python\nSQL' : value));
    fireEvent.submit(screen.getByRole('form', {name: `${singular} editor`}));
    const updatePayload = {...payload} as Record<string,unknown>; if (section === 'skills') delete updatePayload.category;
    await waitFor(() => expect(api.saveProfileEntry).toHaveBeenLastCalledWith(section, updatePayload, 'entry'));
    await waitFor(() => expect(screen.queryByRole('form', {name: `${singular} editor`})).not.toBeInTheDocument());
    fireEvent.click(scoped.getByRole('button', {name: `Remove ${singular}`}));
    await screen.findByText(`${singular} removed.`);
    expect(api.deleteProfileEntry).toHaveBeenCalledWith(section, 'entry');
    expect(scoped.queryByRole('button', {name: `Edit ${singular}`})).not.toBeInTheDocument();
  });
  it('validates date ordering, clears end date for current roles and exposes entry errors', async () => {
    api.saveProfileEntry.mockRejectedValue(new Error('Entry unavailable'));
    render(<ProfileClient/>);
    fireEvent.click(await screen.findByRole('button', {name: 'Add Experience'}));
    change('Company', 'Acme'); change('Role title', 'Engineer'); change('Start date', '2022-01-01'); change('End date', '2021-01-01');
    fireEvent.submit(screen.getByRole('form', {name: 'Experience editor'}));
    expect(await screen.findByText('End date cannot be before start date.')).toBeInTheDocument();
    expect(api.saveProfileEntry).not.toHaveBeenCalled();
    fireEvent.click(screen.getByLabelText('Current role'));
    expect(screen.getByLabelText('End date')).toBeDisabled();
    fireEvent.submit(screen.getByRole('form', {name: 'Experience editor'}));
    expect(await screen.findByText('Entry unavailable')).toBeInTheDocument();
    expect(api.saveProfileEntry.mock.calls[0][1].end_date).toBeNull();
    expect(screen.getByLabelText('Company')).toHaveValue('Acme');
  });
});
