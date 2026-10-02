import React from 'react';
import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import {beforeEach, expect, it, vi} from 'vitest';
import {JobDetailClient} from '../app/jobs/[id]/JobDetailClient';
import {ApplicationDetailClient} from '../components/applications/ApplicationDetailClient';
import {ApplicationsClient} from '../components/applications/ApplicationsClient';
import {ApiError, type Application, type JobDetailResponse, type MatchResultResponse, type SearchProfileResponse} from '../lib/api/types';

const api = vi.hoisted(() => ({getJobById:vi.fn(), listSearchProfiles:vi.fn(), getSavedMatch:vi.fn(), evaluateMatch:vi.fn(), analyzeMatch:vi.fn(), listApplications:vi.fn(), createApplication:vi.fn(), getApplication:vi.fn(), updateApplicationStatus:vi.fn()}));
vi.mock('../lib/api/jobs', () => ({getJobById:api.getJobById}));
vi.mock('../lib/api/search_profiles', () => ({listSearchProfiles:api.listSearchProfiles}));
vi.mock('../lib/api/matching', () => ({getSavedMatch:api.getSavedMatch,evaluateMatch:api.evaluateMatch,analyzeMatch:api.analyzeMatch}));
vi.mock('../lib/api/applications', () => ({listApplications:api.listApplications,createApplication:api.createApplication,getApplication:api.getApplication,updateApplicationStatus:api.updateApplicationStatus}));
vi.mock('next/navigation', () => ({useRouter:() => ({push:vi.fn(),refresh:vi.fn()})}));
const profiles = ['a','b'].map(id => ({id,name:id,base_profile_id:'base',target_roles:[],target_skills:[],locations:[],work_modes:[],industries:[],seniority:null,salary_min:null,salary_max:null,created_at:null,updated_at:null})) satisfies SearchProfileResponse[];
const job: JobDetailResponse = {id:'job',source_id:'source',canonical_url:'https://example.com/job',company:'Acme',title:'Engineer',status:'CLOSED',description:'Python engineer',responsibilities:null,content_hash:'hash',external_job_id:null,location:null,work_mode:null,employment_type:null,salary:null,published_at:null,first_seen_at:null,last_seen_at:null,closed_at:null,created_at:null,updated_at:null,source_name:null,ats_type:null,source_url:null};
const match = (profile='a'): MatchResultResponse => ({id:'match',job_id:'job',search_profile_id:profile,base_profile_id:'base',overall_score:10,deterministic_score:10,final_score:10,confidence:20,category_scores:{},requirement_matches:[],explanation:null,created_at:null,updated_at:null});
const initial: Application = {id:'app',job_id:'job',user_id:'user',status:'INTERESTED',notes:null,created_at:null,updated_at:null,job:{id:'job',canonical_url:job.canonical_url,title:job.title,company:job.company,status:'CLOSED',location:null,work_mode:null,employment_type:null,salary:null,source_name:null},status_history:[]};
beforeEach(() => {
  vi.resetAllMocks(); localStorage.clear(); sessionStorage.clear();
  api.getJobById.mockResolvedValue(job); api.listSearchProfiles.mockResolvedValue(profiles);
  api.getSavedMatch.mockImplementation((_job,profile) => Promise.resolve(match(profile)));
  api.listApplications.mockResolvedValue({items:[],total:0,limit:1,offset:0}); api.createApplication.mockResolvedValue(initial);
});
it('Job Detail can track without any profile, deterministic result or AI', async () => {
  api.listSearchProfiles.mockResolvedValue([]);
  render(<JobDetailClient jobId="job" />);
  fireEvent.click(await screen.findByRole('button',{name:'Track Application'}));
  expect(await screen.findByRole('link',{name:'Manage application'})).toHaveAttribute('href','/applications/app');
  expect(api.evaluateMatch).not.toHaveBeenCalled(); expect(api.analyzeMatch).not.toHaveBeenCalled();
});
it('AI failure and SearchProfile switching leave the same tracked application manageable', async () => {
  api.analyzeMatch.mockRejectedValue(new ApiError(503,'AI disabled'));
  render(<JobDetailClient jobId="job" />);
  fireEvent.click(await screen.findByRole('button',{name:'AI ile Detaylı Analiz Et'}));
  await screen.findByText(/AI disabled/); fireEvent.click(screen.getByRole('button',{name:'Track Application'}));
  await screen.findByRole('link',{name:'Manage application'});
  fireEvent.change(screen.getByTestId('search-profile-selector'),{target:{value:'b'}});
  await waitFor(() => expect(api.getSavedMatch).toHaveBeenLastCalledWith('job','b',expect.any(AbortSignal)));
  expect(screen.getByRole('link',{name:'Manage application'})).toHaveAttribute('href','/applications/app');
  expect(api.createApplication).toHaveBeenCalledTimes(1); expect(api.listApplications).toHaveBeenCalledTimes(1);
});
it('explicit deterministic calculation flows into tracking, list, status changes and persisted history', async () => {
  api.getSavedMatch.mockRejectedValue(new ApiError(404,'Missing match','MATCH_RESULT_NOT_FOUND')); api.evaluateMatch.mockImplementation(({search_profile_id}) => Promise.resolve(match(search_profile_id)));
  let view = render(<JobDetailClient jobId="job" />);
  fireEvent.click(await screen.findByRole('button',{name:'Calculate Match'})); await screen.findByRole('button',{name:'AI ile Detaylı Analiz Et'});
  fireEvent.click(screen.getByRole('button',{name:'Track Application'})); await screen.findByRole('link',{name:'Manage application'});
  view.unmount(); api.listApplications.mockResolvedValue({items:[initial],total:1,limit:20,offset:0});
  view = render(<ApplicationsClient />); expect(await screen.findByRole('link',{name:'Manage application'})).toHaveAttribute('href','/applications/app');
  view.unmount(); api.getApplication.mockResolvedValue(initial); let current = initial;
  api.updateApplicationStatus.mockImplementation(async (_id,status) => {
    current = {...current,status,status_history:[...current.status_history,{id:status,application_id:'app',from_status:current.status,to_status:status,changed_at:'2026-10-02T12:00:00Z'}]}; return current;
  });
  render(<ApplicationDetailClient applicationId="app" />); await screen.findByText('Engineer');
  for (const status of ['APPLYING','APPLIED','INTERVIEW']) {
    fireEvent.change(screen.getByLabelText('New status'),{target:{value:status}}); fireEvent.click(screen.getByRole('button',{name:'Update status'}));
    await waitFor(() => expect(screen.getByRole('button',{name:'Update status'})).toBeDisabled());
    await waitFor(() => expect(screen.getByLabelText('New status')).toHaveValue(''));
  }
  expect(screen.getAllByRole('listitem').map(el => el.textContent)).toEqual([expect.stringContaining('Interested → Applying'),expect.stringContaining('Applying → Applied'),expect.stringContaining('Applied → Interview')]);
});
