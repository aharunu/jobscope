import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { JobCard } from '../components/jobs/JobCard';
import { JobSummaryResponse } from '../lib/api/types';

const navigation = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock('next/navigation', () => ({
  useRouter: () => navigation,
}));

const mockJob: JobSummaryResponse = {
  id: '3fa85f64-5717-4562-b3fc-2c963f66afa6',
  source_id: '4fa85f64-5717-4562-b3fc-2c963f66afa6',
  canonical_url: 'https://jobs.lever.co/acme/12345',
  company: 'Acme Corp',
  title: 'Senior Backend Engineer',
  status: 'ACTIVE',
  external_job_id: '12345',
  location: 'Berlin, Germany',
  work_mode: 'Remote',
  employment_type: 'Full-time',
  salary: '€85,000 - €95,000',
  published_at: new Date().toISOString(),
  first_seen_at: new Date().toISOString(),
  last_seen_at: new Date().toISOString(),
  closed_at: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  source_name: 'Acme Careers',
  ats_type: 'lever',
  source_url: 'https://jobs.lever.co/acme',
};

describe('JobCard Component', () => {
  it('renders all key job metadata accurately', () => {
    render(<JobCard job={mockJob} />);

    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('Senior Backend Engineer')).toBeInTheDocument();
    expect(screen.getByText('Berlin, Germany')).toBeInTheDocument();
    expect(screen.getByText('Remote')).toBeInTheDocument();
    expect(screen.getByText('Full-time')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('€85,000 - €95,000')).toBeInTheDocument();
    expect(screen.getByText('Acme Careers')).toBeInTheDocument();
  });

  it('renders external application link with security attributes', () => {
    render(<JobCard job={mockJob} />);

    const applyLink = screen.getByRole('link', { name: /apply on company website/i });
    expect(applyLink).toHaveAttribute('href', 'https://jobs.lever.co/acme/12345');
    expect(applyLink).toHaveAttribute('target', '_blank');
    expect(applyLink).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('renders closed badge for closed status', () => {
    const closedJob = { ...mockJob, status: 'CLOSED' };
    render(<JobCard job={closedJob} />);

    expect(screen.getByText('Closed')).toBeInTheDocument();
  });

  it('opens the job with the keyboard without hijacking the nested Apply link', () => {
    navigation.push.mockClear();
    render(<JobCard job={mockJob} />);
    fireEvent.keyDown(screen.getByRole('link', {name: /apply on company website/i}), {key: 'Enter'});
    expect(navigation.push).not.toHaveBeenCalled();
    fireEvent.keyDown(screen.getByRole('link', {name: /view details for/i}), {key: 'Enter'});
    expect(navigation.push).toHaveBeenCalledWith(`/jobs/${mockJob.id}`);
  });
});
