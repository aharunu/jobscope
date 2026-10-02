import {beforeEach, expect, it, vi} from 'vitest';
import {createApplication, deleteApplication, getApplication, getApplicationHistory, listApplications, updateApplicationNotes, updateApplicationStatus} from '../lib/api/applications';
beforeEach(() => {vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,status:200,json:async () => ({})}));});
it('uses central identity/error transport, safe creation payload and uncached reads', async () => {
  const signal = new AbortController().signal;
  await listApplications({job_id:'job',status:'INTERVIEW',limit:1},signal);
  expect(fetch).toHaveBeenLastCalledWith('/api/applications?job_id=job&status=INTERVIEW&limit=1',expect.objectContaining({cache:'no-store',signal}));
  await createApplication('job',signal);
  expect(fetch).toHaveBeenLastCalledWith('/api/applications',expect.objectContaining({method:'POST',body:JSON.stringify({job_id:'job',status:'INTERESTED'}),signal}));
  await getApplication('app',signal); await updateApplicationStatus('app','APPLIED',signal); await updateApplicationNotes('app',null,signal); await getApplicationHistory('app',signal); await deleteApplication('app',signal);
  expect(fetch).toHaveBeenLastCalledWith('/api/applications/app',expect.objectContaining({method:'DELETE',signal}));
});
