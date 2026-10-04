'use client';

import React, {useEffect, useId, useRef, useState} from 'react';
import {deleteProfileEntry, getSkillSuggestions, saveProfileEntry, type ProfileSectionName, type ProfileEntry} from '@/lib/api/profile';
import {Input} from '@/components/ui/Input';
import {Button} from '@/components/ui/Button';
import {Alert} from '@/components/ui/Alert';

type Field = {key: string; label: string; type?: 'number' | 'date' | 'checkbox' | 'list' | 'textarea' | 'url'; required?: boolean; max?: number; min?: number; maxLength?: number};
const sections: Record<ProfileSectionName, {title: string; singular: string; fields: Field[]}> = {
  skills: {title: 'Skills', singular: 'Skill', fields: [
    {key: 'name', label: 'Skill name', required: true, maxLength: 150},
    {key: 'years_of_experience', label: 'Years of experience', type: 'number', min: 0, max: 50}, {key: 'level', label: 'Level', maxLength: 50},
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

const levels = ['BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT'];
const minimumDate = '1900-01-01';
const todayDate = () => { const now = new Date(); return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`; };
const validDate = (value: string) => /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0,10) === value;

export function ProfileSection({section, entries, onSaved}: {section: ProfileSectionName; entries: ProfileEntry[]; onSaved: (entry: ProfileEntry | null, deletedId?: string) => void}) {
  const config = sections[section];
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, string | boolean>>({});
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string,string>>({});
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [suggestionError, setSuggestionError] = useState(false);
  const [legacyLevel, setLegacyLevel] = useState('');
  const [legacyDate, setLegacyDate] = useState(false);
  const listId = useId();
  const today = todayDate();
  const skillQuery = String(draft.name ?? '');
  useEffect(() => {
    if (section !== 'skills' || editing === null) return;
    const controller = new AbortController(); setSuggestions([]); setSuggestionError(false);
    const timer = setTimeout(() => {
      getSkillSuggestions(skillQuery.slice(0,100), controller.signal).then(names => {
        if (!controller.signal.aborted) setSuggestions(names);
      }).catch(() => {if (!controller.signal.aborted) setSuggestionError(true);});
    }, 150);
    return () => {clearTimeout(timer); controller.abort();};
  }, [section, editing, skillQuery]);
  const begin = (entry?: ProfileEntry) => {
    const source = entry ? Object.fromEntries(Object.entries(entry)) : {};
    const values = Object.fromEntries(config.fields.map(f => [f.key, f.type === 'checkbox' ? Boolean(source[f.key]) : Array.isArray(source[f.key]) ? source[f.key].join('\n') : String(source[f.key] ?? '')]));
    let invalidSavedDate = false;
    for (const key of ['start_date', 'end_date']) {
      if (source[key] && (!validDate(String(source[key])) || String(source[key]) < minimumDate || String(source[key]) > today)) {values[key] = ''; invalidSavedDate = true;}
    }
    if (values.is_current) values.end_date = '';
    const oldLevel = String(source.level ?? '');
    setLegacyLevel(oldLevel && !levels.includes(oldLevel) ? oldLevel : '');
    setLegacyDate(invalidSavedDate); setErrors({}); setDraft(values);
    setEditing(entry?.id ?? 'new'); setError(null); setSuccess(null);
  };
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); if (lock.current) return;
    const payload: Record<string, unknown> = {};
    const invalid: Record<string,string> = {};
    for (const field of config.fields) {
      const raw = draft[field.key] ?? '';
      if (field.required && !String(raw).trim()) invalid[field.key] = `${field.label} is required.`;
      if (field.maxLength && String(raw).length > field.maxLength) invalid[field.key] = `${field.label} must be at most ${field.maxLength} characters.`;
      if (field.type === 'url' && String(raw).trim()) {
        try {new URL(String(raw).trim());} catch {invalid[field.key] = 'Enter a valid project URL.';}
      }
      payload[field.key] = field.type === 'checkbox' ? Boolean(raw) : field.type === 'list' ? String(raw).split('\n').map(s => s.trim()).filter(Boolean) : field.type === 'number' ? raw === '' ? null : Number(raw) : String(raw).trim() || null;
      if (field.type === 'number' && raw !== '') {
        const value = Number(raw);
        if (!Number.isFinite(value) || value < field.min! || value > field.max!) invalid[field.key] = `${field.label} must be between ${field.min} and ${field.max}.`;
        else if (field.key === 'years_of_experience' ? !Number.isInteger(value * 2) : !Number.isInteger(value)) invalid[field.key] = field.key === 'years_of_experience' ? 'Use increments of 0.5 years.' : 'Use a whole year.';
      }
      if (field.type === 'list' && ((payload[field.key] as string[]).length > 50 || (payload[field.key] as string[]).some(s => s.length > 150))) invalid[field.key] = 'Use at most 50 skills, each at most 150 characters.';
    }
    if (payload.is_current) payload.end_date = null;
    for (const key of ['start_date','end_date']) {
      const value = payload[key];
      if (value && (!validDate(String(value)) || String(value) < minimumDate)) invalid[key] = `${key === 'start_date' ? 'Start' : 'End'} date must be on or after 1900-01-01.`;
      else if (value && String(value) > today) invalid[key] = `${key === 'start_date' ? 'Start' : 'End'} date cannot be in the future.`;
    }
    if (payload.end_date && payload.start_date && String(payload.end_date) < String(payload.start_date)) invalid.end_date = 'End date cannot be before start date.';
    if (payload.start_year && payload.end_year && Number(payload.end_year) < Number(payload.start_year)) invalid.end_year = 'End year cannot be before start year.';
    if (section === 'skills') {
      if (editing === 'new') payload.category = null;
      if (payload.level === legacyLevel && legacyLevel) delete payload.level; // Preserve historical metadata unless explicitly replaced.
      else if (payload.level && !levels.includes(String(payload.level))) invalid.level = 'Choose a listed proficiency level.';
    }
    setErrors(invalid); if (Object.keys(invalid).length) return;
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
        <div>{config.fields.map(field => <p key={field.key}><strong>{field.label}: </strong>{field.type === 'checkbox' ? values[field.key] ? 'Yes' : 'No' : field.type === 'date' && values[field.key] && String(values[field.key]) < minimumDate ? 'Invalid saved date — edit to correct' : Array.isArray(values[field.key]) ? values[field.key].join(', ') : String(values[field.key] ?? '—')}</p>)}</div>
        <div className="profile-actions"><Button variant="secondary" disabled={busy || editing !== null} onClick={() => begin(entry)}>Edit {config.singular}</Button><Button variant="ghost" disabled={busy || editing !== null} onClick={() => remove(entry)}>Remove {config.singular}</Button></div>
      </article>;
    })}
    {editing !== null && <form noValidate onSubmit={save} className="profile-editor" aria-label={`${config.singular} editor`}>
      <h3>{editing === 'new' ? 'Add' : 'Edit'} {config.singular}</h3>
      {legacyDate && <Alert variant="warning">This saved experience has an invalid date. Choose the actual date before saving; no replacement date has been invented.</Alert>}
      {legacyLevel && <p className="text-muted">Existing level “{legacyLevel}” is retained unless you choose a new level.</p>}
      <fieldset disabled={busy} className={`profile-fieldset ${section === 'experiences' ? 'profile-experience-fields' : ''}`}>
        {config.fields.filter(field => field.key !== 'is_current').map(field => {
          const change = (value: string) => {
            setDraft(current => ({...current, [field.key]: value}));
            setErrors(current => {const next = {...current}; delete next[field.key]; return next;});
          };
          const control = field.key === 'level' ? <label>Level<select className="select" value={String(draft.level ?? '')} onChange={e => change(e.target.value)}>
            <option value="">Not specified</option>{legacyLevel && <option value={legacyLevel}>Existing: {legacyLevel}</option>}
            {levels.map(level => <option key={level} value={level}>{level.charAt(0)+level.slice(1).toLowerCase()}</option>)}
          </select>{errors.level && <span role="alert" className="profile-field-error">{errors.level}</span>}</label> : field.type === 'textarea' || field.type === 'list' ? <label>{field.label}<textarea className="input" value={String(draft[field.key] ?? '')} onChange={e => change(e.target.value)}/>{errors[field.key] && <span role="alert" className="profile-field-error">{errors[field.key]}</span>}</label> :
            <Input label={`${field.label}${field.required ? ' *' : ''}`} aria-label={field.label} error={errors[field.key]} type={field.type ?? 'text'} required={field.required} min={field.type === 'date' ? minimumDate : field.min} max={field.type === 'date' ? today : field.max} maxLength={field.maxLength} step={field.key === 'years_of_experience' ? '0.5' : '1'} list={field.key === 'name' && section === 'skills' ? listId : undefined} disabled={field.key === 'end_date' && Boolean(draft.is_current)} value={String(draft[field.key] ?? '')} onChange={e => change(e.target.value)}/>;
          return <div key={field.key} className={field.type === 'textarea' || field.type === 'list' ? 'profile-wide-field' : 'profile-field-group'}>
            {control}
            {field.key === 'end_date' && <label className="profile-checkbox"><input type="checkbox" checked={Boolean(draft.is_current)} onChange={e => {
              const checked = e.target.checked;
              setDraft(current => ({...current,is_current:checked,...(checked ? {end_date:''} : {})}));
              if (e.target.checked) setErrors(current => {const next = {...current}; delete next.end_date; return next;});
            }}/>Current role</label>}
            {field.key === 'name' && section === 'skills' && <>
              <datalist id={listId}>{suggestions.map(name => <option key={name} value={name}/>)}</datalist>
              <p className="text-muted">Type to search known skills, or enter your own skill.</p>
              {suggestionError && <p className="text-muted">Suggestions unavailable. You can still enter a custom skill.</p>}
            </>}
          </div>;
        })}
      </fieldset>
      <div className="profile-actions"><Button type="submit" disabled={busy}>{busy ? 'Saving...' : `Save ${config.singular}`}</Button><Button type="button" variant="secondary" disabled={busy} onClick={() => setEditing(null)}>Cancel</Button></div>
    </form>}
  </section>;
}
