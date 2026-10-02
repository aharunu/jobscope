'use client';

import React, {useRef, useState} from 'react';
import {deleteProfileEntry, saveProfileEntry, type ProfileSectionName, type ProfileEntry} from '@/lib/api/profile';
import {Input} from '@/components/ui/Input';
import {Button} from '@/components/ui/Button';
import {Alert} from '@/components/ui/Alert';

type Field = {key: string; label: string; type?: 'number' | 'date' | 'checkbox' | 'list' | 'textarea' | 'url'; required?: boolean; max?: number; min?: number; maxLength?: number};
const sections: Record<ProfileSectionName, {title: string; singular: string; fields: Field[]}> = {
  skills: {title: 'Skills', singular: 'Skill', fields: [
    {key: 'name', label: 'Skill name', required: true, maxLength: 150}, {key: 'category', label: 'Category', maxLength: 100},
    {key: 'years_of_experience', label: 'Years of experience', type: 'number', min: 0, max: 99.9}, {key: 'level', label: 'Level', maxLength: 50},
  ]},
  experiences: {title: 'Experience', singular: 'Experience', fields: [
    {key: 'company', label: 'Company', required: true, maxLength: 255}, {key: 'title', label: 'Role title', required: true, maxLength: 255},
    {key: 'start_date', label: 'Start date', type: 'date', required: true}, {key: 'end_date', label: 'End date', type: 'date'},
    {key: 'is_current', label: 'Current role', type: 'checkbox'}, {key: 'description', label: 'Description', type: 'textarea'},
    {key: 'skills_used', label: 'Skills used (one per line)', type: 'list'},
  ]},
  educations: {title: 'Education', singular: 'Education', fields: [
    {key: 'school', label: 'School', required: true, maxLength: 255}, {key: 'degree', label: 'Degree', required: true, maxLength: 100},
    {key: 'field_of_study', label: 'Field of study', required: true, maxLength: 255},
    {key: 'start_year', label: 'Start year', type: 'number', min: 1900, max: 2100}, {key: 'end_year', label: 'End year', type: 'number', min: 1900, max: 2100},
  ]},
  projects: {title: 'Projects', singular: 'Project', fields: [
    {key: 'title', label: 'Project title', required: true, maxLength: 255}, {key: 'description', label: 'Description', type: 'textarea'},
    {key: 'skills_used', label: 'Skills used (one per line)', type: 'list'}, {key: 'url', label: 'Project URL', type: 'url', maxLength: 2048},
  ]},
};

export function ProfileSection({section, entries, onSaved}: {section: ProfileSectionName; entries: ProfileEntry[]; onSaved: (entry: ProfileEntry | null, deletedId?: string) => void}) {
  const config = sections[section];
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, string | boolean>>({});
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const begin = (entry?: ProfileEntry) => {
    const source = entry ? Object.fromEntries(Object.entries(entry)) : {};
    setDraft(Object.fromEntries(config.fields.map(f => [f.key, f.type === 'checkbox' ? Boolean(source[f.key]) : Array.isArray(source[f.key]) ? source[f.key].join('\n') : String(source[f.key] ?? '')])));
    setEditing(entry?.id ?? 'new'); setError(null); setSuccess(null);
  };
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); if (lock.current) return;
    const payload: Record<string, unknown> = {};
    for (const field of config.fields) {
      const raw = draft[field.key] ?? '';
      if (field.required && !String(raw).trim()) {setError(`${field.label} is required.`); return;}
      payload[field.key] = field.type === 'checkbox' ? Boolean(raw) : field.type === 'list' ? String(raw).split('\n').map(s => s.trim()).filter(Boolean) : field.type === 'number' ? raw === '' ? null : Number(raw) : String(raw).trim() || null;
      if (field.type === 'list' && ((payload[field.key] as string[]).length > 50 || (payload[field.key] as string[]).some(s => s.length > 150))) {setError('Use at most 50 skills, each at most 150 characters.'); return;}
    }
    if (payload.is_current) payload.end_date = null;
    if (payload.end_date && String(payload.end_date) < String(payload.start_date)) {setError('End date cannot be before start date.'); return;}
    if (payload.start_year && payload.end_year && Number(payload.end_year) < Number(payload.start_year)) {setError('End year cannot be before start year.'); return;}
    lock.current = true; setBusy(true); setError(null);
    try {const saved = await saveProfileEntry(section, payload, editing === 'new' ? undefined : editing ?? undefined); onSaved(saved); setEditing(null); setSuccess(`${config.singular} saved.`);}
    catch (err) {setError(err instanceof Error ? err.message : 'Unable to save entry.');}
    finally {lock.current = false; setBusy(false);}
  };
  const remove = async (entry: ProfileEntry) => {
    if (lock.current || !window.confirm(`Remove this ${config.singular.toLowerCase()}?`)) return;
    lock.current = true; setBusy(true); setError(null);
    try {await deleteProfileEntry(section, entry.id); onSaved(null, entry.id); setSuccess(`${config.singular} removed.`);}
    catch (err) {setError(err instanceof Error ? err.message : 'Unable to remove entry.');}
    finally {lock.current = false; setBusy(false);}
  };
  return <section className="card profile-section" aria-label={config.title}>
    <div className="profile-section-header"><h2>{config.title}</h2><Button variant="secondary" disabled={busy || editing !== null} onClick={() => begin()}>Add {config.singular}</Button></div>
    {error && <Alert variant="danger">{error}</Alert>}{success && <p role="status">{success}</p>}
    {!entries.length && <p className="text-muted">No {config.title.toLowerCase()} added yet.</p>}
    {entries.map(entry => {
      const values = Object.fromEntries(Object.entries(entry));
      return <article key={entry.id} className="profile-entry">
        <div>{config.fields.map(field => <p key={field.key}><strong>{field.label}: </strong>{field.type === 'checkbox' ? values[field.key] ? 'Yes' : 'No' : Array.isArray(values[field.key]) ? values[field.key].join(', ') : String(values[field.key] ?? '—')}</p>)}</div>
        <div className="profile-actions"><Button variant="secondary" disabled={busy || editing !== null} onClick={() => begin(entry)}>Edit {config.singular}</Button><Button variant="ghost" disabled={busy || editing !== null} onClick={() => remove(entry)}>Remove {config.singular}</Button></div>
      </article>;
    })}
    {editing !== null && <form onSubmit={save} className="profile-editor" aria-label={`${config.singular} editor`}>
      <h3>{editing === 'new' ? 'Add' : 'Edit'} {config.singular}</h3>
      <fieldset disabled={busy} className="profile-fieldset">
        {config.fields.map(field => field.type === 'textarea' || field.type === 'list' ? <label key={field.key}>{field.label}<textarea className="input" value={String(draft[field.key] ?? '')} onChange={e => setDraft({...draft, [field.key]: e.target.value})}/></label> :
          field.type === 'checkbox' ? <label key={field.key} className="profile-checkbox"><input type="checkbox" checked={Boolean(draft[field.key])} onChange={e => setDraft({...draft, [field.key]: e.target.checked})}/>{field.label}</label> :
          <Input key={field.key} label={field.label} type={field.type ?? 'text'} required={field.required} min={field.min} max={field.max} maxLength={field.maxLength} step={field.key === 'years_of_experience' ? '0.1' : '1'} disabled={field.key === 'end_date' && Boolean(draft.is_current)} value={String(draft[field.key] ?? '')} onChange={e => setDraft({...draft, [field.key]: e.target.value})}/>
        )}
      </fieldset>
      <div className="profile-actions"><Button type="submit" disabled={busy}>{busy ? 'Saving...' : `Save ${config.singular}`}</Button><Button type="button" variant="secondary" disabled={busy} onClick={() => setEditing(null)}>Cancel</Button></div>
    </form>}
  </section>;
}
