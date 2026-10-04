import React from 'react';
import {act, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {beforeEach, expect, it, vi} from 'vitest';
import {SearchProfilesClient} from '@/app/search-profiles/SearchProfilesClient';
import {ApiError, type SearchProfileResponse} from '@/lib/api/types';

const api = vi.hoisted(() => ({listSearchProfiles:vi.fn(), updateSearchProfile:vi.fn(), createSearchProfile:vi.fn(), deleteSearchProfile:vi.fn()}));
vi.mock('@/lib/api/search_profiles', () => api);
vi.mock('next/navigation', () => ({useRouter:()=>({push:vi.fn()}), useSearchParams:()=>({get:()=>null})}));
const original: SearchProfileResponse = {
  id:'search-1', base_profile_id:'base-1', name:'Backend Search', seniority:'Senior',
  target_roles:['Backend Engineer'], target_skills:['Python'], locations:['Washington, DC'],
  work_modes:['Remote'], industries:['FinTech'], salary_min:100000, salary_max:150000,
  created_at:null, updated_at:null,
};
beforeEach(()=>{vi.resetAllMocks();api.listSearchProfiles.mockResolvedValue([original]);});
async function edit() {
  await screen.findByTestId('edit-profile-btn-search-1');
  fireEvent.click(screen.getByRole('button',{name:'Edit Backend Search'}));
  return screen.getByRole('form',{name:'Edit Search Profile'});
}
const change=(id:string,value:string)=>fireEvent.change(screen.getByTestId(id),{target:{value}});

it('opens existing profile for editing with every persisted form value',async()=>{
  render(<SearchProfilesClient/>);await edit();
  for(const [id,value] of [['name','Backend Search'],['seniority','Senior'],['target-roles','Backend Engineer'],['target-skills','Python'],['locations','Washington, DC'],['industries','FinTech']]) {
    expect(screen.getByTestId(`profile-${id}-input`)).toHaveValue(value);
  }
  expect(screen.getByTestId('profile-salary-min-input')).toHaveValue(100000);
  expect(screen.getByTestId('profile-salary-max-input')).toHaveValue(150000);
  expect(screen.getByTestId('work-mode-toggle-remote')).toHaveTextContent('✓');
  fireEvent.click(screen.getByRole('button',{name:'Junior'}));
  fireEvent.click(screen.getByRole('button',{name:'Mid-Level'}));
  expect(screen.getByTestId('profile-seniority-input')).toHaveValue('Mid-Level');
});

it('saves through update and renders authoritative response, then restores it on page remount',async()=>{
  let stored=original;
  api.listSearchProfiles.mockImplementation(async()=>[stored]);
  api.updateSearchProfile.mockImplementation(async()=>{stored={...original,name:'Canonical Backend',seniority:'Lead',target_roles:['Platform Engineer'],salary_min:120000};return stored;});
  const view=render(<SearchProfilesClient/>);const form=await edit();
  change('profile-name-input','  Edited Backend  ');change('profile-target-roles-input','Platform Engineer');
  fireEvent.submit(form);
  await screen.findByText('Search profile updated.');
  expect(api.updateSearchProfile).toHaveBeenCalledWith('search-1',expect.objectContaining({name:'Edited Backend',target_roles:['Platform Engineer'],locations:['Washington, DC'],seniority:'Senior'}));
  expect(screen.getByRole('heading',{name:'Canonical Backend'})).toBeInTheDocument();
  expect(api.createSearchProfile).not.toHaveBeenCalled();
  view.unmount();render(<SearchProfilesClient/>);
  await screen.findByRole('heading',{name:'Canonical Backend'});
  fireEvent.click(screen.getByRole('button',{name:'Edit Canonical Backend'}));
  expect(screen.getByTestId('profile-name-input')).toHaveValue('Canonical Backend');
  expect(screen.getByTestId('profile-seniority-input')).toHaveValue('Lead');
  expect(screen.getByTestId('profile-salary-min-input')).toHaveValue(120000);
  expect(api.listSearchProfiles).toHaveBeenCalledTimes(2);
});

it('preserves draft and existing safe error UI on failed update, allowing retry',async()=>{
  api.updateSearchProfile.mockRejectedValueOnce(new ApiError(500,'Update unavailable')).mockResolvedValueOnce({...original,name:'My draft'});
  render(<SearchProfilesClient/>);const form=await edit();change('profile-name-input','My draft');
  fireEvent.submit(form);await screen.findByText('Update unavailable');
  expect(screen.getByText('Server Error')).toBeInTheDocument();
  expect(screen.getByTestId('profile-name-input')).toHaveValue('My draft');
  fireEvent.submit(form);await screen.findByText('Search profile updated.');
  expect(api.updateSearchProfile).toHaveBeenCalledTimes(2);
});

it('cancel discards unsaved changes without any mutation and reopening restores persisted data',async()=>{
  render(<SearchProfilesClient/>);await edit();change('profile-name-input','Discard me');
  fireEvent.click(screen.getByRole('button',{name:'Cancel'}));
  expect(screen.getByRole('heading',{name:'Backend Search'})).toBeInTheDocument();
  expect(api.updateSearchProfile).not.toHaveBeenCalled();expect(api.createSearchProfile).not.toHaveBeenCalled();expect(api.deleteSearchProfile).not.toHaveBeenCalled();
  await edit();expect(screen.getByTestId('profile-name-input')).toHaveValue('Backend Search');
});

it('blocks duplicate submissions synchronously and locks fields and cancellation until completion',async()=>{
  let finish!:(value:SearchProfileResponse)=>void;
  api.updateSearchProfile.mockReturnValue(new Promise(resolve=>{finish=resolve;}));
  render(<SearchProfilesClient/>);const form=await edit();
  act(()=>{fireEvent.submit(form);fireEvent.submit(form);});
  expect(api.updateSearchProfile).toHaveBeenCalledTimes(1);
  expect(within(form).getByRole('button',{name:/Loading/})).toBeDisabled();
  expect(screen.getByTestId('profile-name-input')).toBeDisabled();
  expect(screen.getByRole('button',{name:'Cancel'})).toBeDisabled();
  await act(async()=>finish(original));await screen.findByText('Search profile updated.');
});

it('validates edited fields before submitting and supports clearing optional criteria',async()=>{
  api.updateSearchProfile.mockResolvedValue({...original,seniority:null,salary_min:null,salary_max:null});
  render(<SearchProfilesClient/>);const form=await edit();change('profile-name-input','   ');fireEvent.submit(form);
  expect(api.updateSearchProfile).not.toHaveBeenCalled();expect(screen.getByText(/Profile name is required/)).toBeInTheDocument();
  change('profile-name-input','Backend Search');change('profile-seniority-input','');change('profile-salary-min-input','');change('profile-salary-max-input','');fireEvent.submit(form);
  await waitFor(()=>expect(api.updateSearchProfile).toHaveBeenCalledWith('search-1',expect.objectContaining({seniority:null,salary_min:null,salary_max:null})));
});
