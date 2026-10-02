import { apiClient } from './client';

export interface ProfileSkill {
  id: string; base_profile_id: string; name: string; category: string | null;
  years_of_experience: number | string | null; level: string | null;
}
export interface ProfileExperience {
  id: string; base_profile_id: string; company: string; title: string; description: string | null;
  start_date: string; end_date: string | null; is_current: boolean; skills_used: string[];
}
export interface ProfileEducation {
  id: string; base_profile_id: string; school: string; degree: string; field_of_study: string;
  start_year: number | null; end_year: number | null;
}
export interface ProfileProject {
  id: string; base_profile_id: string; title: string; description: string | null; skills_used: string[]; url: string | null;
}
export interface BaseProfileResponse {
  id: string; user_id: string; name: string; summary: string | null;
  skills: ProfileSkill[]; experiences: ProfileExperience[]; educations: ProfileEducation[]; projects: ProfileProject[];
}
export type ProfileSectionName = 'skills' | 'experiences' | 'educations' | 'projects';
export type ProfileEntry = ProfileSkill | ProfileExperience | ProfileEducation | ProfileProject;
export const getProfile = (signal?: AbortSignal) => apiClient<BaseProfileResponse>('/api/profile', {signal, cache: 'no-store'});
export const updateProfile = (payload: {name: string; summary: string | null}) => apiClient<BaseProfileResponse>('/api/profile', {method: 'PATCH', body: JSON.stringify(payload)});
export const saveProfileEntry = (section: ProfileSectionName, payload: Record<string, unknown>, id?: string) =>
  apiClient<ProfileEntry>(`/api/profile/${section}${id ? `/${encodeURIComponent(id)}` : ''}`, {method: id ? 'PATCH' : 'POST', body: JSON.stringify(payload)});
export const deleteProfileEntry = (section: ProfileSectionName, id: string) =>
  apiClient<void>(`/api/profile/${section}/${encodeURIComponent(id)}`, {method: 'DELETE'});
