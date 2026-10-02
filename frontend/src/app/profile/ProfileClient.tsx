'use client';

import React, {useEffect, useRef, useState} from 'react';
import Link from 'next/link';
import {ApiError} from '@/lib/api/types';
import {getProfile, updateProfile, type BaseProfileResponse, type ProfileSectionName, type ProfileEntry} from '@/lib/api/profile';
import {ProfileSection} from '@/components/profile/ProfileSection';
import {Alert} from '@/components/ui/Alert';
import {Input} from '@/components/ui/Input';
import {Button} from '@/components/ui/Button';

export default function ProfileClient() {
  const [profile, setProfile] = useState<BaseProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState('');
  const [summary, setSummary] = useState('');
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null);
    getProfile(controller.signal).then(value => {if (!controller.signal.aborted) setProfile(value);}).catch(err => {
      if (controller.signal.aborted) return;
      if (err instanceof ApiError && err.isNotFound) setProfile(null);
      else setError(err instanceof Error ? err.message : 'Unable to load profile.');
    }).finally(() => {if (!controller.signal.aborted) setLoading(false);});
    return () => controller.abort();
  }, [attempt]);
  const begin = () => {setName(profile?.name === 'Candidate Profile' ? '' : profile?.name ?? ''); setSummary(profile?.summary ?? ''); setEditing(true); setError(null); setSuccess(null);};
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); if (lock.current) return;
    if (!name.trim()) {setError('Profile name is required.'); return;}
    lock.current = true; setBusy(true); setError(null);
    try {
      if (!profile) await getProfile(); // Existing API creates the blank profile on GET.
      const saved = await updateProfile({name: name.trim(), summary: summary.trim() || null});
      setProfile(current => ({...saved, skills: current?.skills ?? saved.skills, experiences: current?.experiences ?? saved.experiences, educations: current?.educations ?? saved.educations, projects: current?.projects ?? saved.projects}));
      setEditing(false); setSuccess('Profile saved.');
    } catch (err) {setError(err instanceof Error ? err.message : 'Unable to save profile.');}
    finally {lock.current = false; setBusy(false);}
  };
  const changed = (section: ProfileSectionName, entry: ProfileEntry | null, deletedId?: string) => setProfile(current => {
    if (!current) return current;
    const entries = current[section].filter(item => item.id !== (deletedId ?? entry?.id));
    return {...current, [section]: entry ? [...entries, entry] : entries};
  });
  const blank = !profile || (profile.name === 'Candidate Profile' && !profile.summary && !profile.skills.length && !profile.experiences.length && !profile.educations.length && !profile.projects.length);
  return <div className="container profile-page">
    <header><h1>Candidate Profile</h1><p className="text-muted">Your experience and evidence for deterministic matching.</p><Link href="/search-profiles">Configure Search Profiles →</Link></header>
    {loading ? <p role="status">Loading profile...</p> : <>
      {error && <Alert variant="danger">{error}</Alert>}
      {error && !editing && <Button variant="secondary" onClick={() => setAttempt(a => a + 1)}>Retry Profile</Button>}
      {success && <p role="status">{success}</p>}
      {!error && <section className="card profile-section"><div className="profile-section-header"><h2>Profile Summary</h2>{!editing && <Button onClick={begin}>{blank ? 'Create Profile' : 'Edit Profile'}</Button>}</div>
        {!editing ? <>{blank ? <p>Build your profile manually to give matching useful evidence.</p> : <><h3>{profile?.name}</h3><p className="profile-summary">{profile?.summary || 'No summary added yet.'}</p></>}</> : null}
      </section>}
      {editing && <form className="card profile-section profile-editor" onSubmit={save} aria-label="Profile editor"><fieldset disabled={busy} className="profile-fieldset">
        <Input label="Profile name" required maxLength={255} value={name} onChange={e => setName(e.target.value)}/>
        <label>Summary<textarea className="input" value={summary} onChange={e => setSummary(e.target.value)}/></label>
      </fieldset><div className="profile-actions"><Button type="submit" disabled={busy}>{busy ? 'Saving...' : 'Save Profile'}</Button><Button type="button" variant="secondary" disabled={busy} onClick={() => {setEditing(false); setError(null);}}>Cancel</Button></div></form>}
      {profile && (['skills', 'experiences', 'educations', 'projects'] as ProfileSectionName[]).map(section => <ProfileSection key={section} section={section} entries={profile[section]} onSaved={(entry, deletedId) => changed(section, entry, deletedId)}/>)}
    </>}
  </div>;
}
