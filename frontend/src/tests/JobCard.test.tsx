import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { JobCard } from '../components/jobs/JobCard';
import { JobSummaryResponse } from '../lib/api/types';

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
  it('shows and highlights the server-provided description-only context as plain text', () => {
    const { container } = render(<JobCard job={{ ...mockJob, description_match: {
      before: 'Experience with ', match: 'FastAPI', after: ' and Python is required.',
    } }} />);
    expect(screen.getByText('Matched in description:')).toBeInTheDocument();
    expect(container.querySelector('mark')).toHaveTextContent('FastAPI');
    expect(container.querySelector('.job-card-excerpt')).toHaveTextContent('Experience with FastAPI and Python');
  });

  it('does not expose snippet markup as executable HTML', () => {
    const { container } = render(<JobCard job={{ ...mockJob, description_match: {
      before: '<img onerror="alert(1)">', match: '<script>', after: '</script>',
    } }} />);
    expect(container.querySelector('script')).toBeNull();
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('mark')).toHaveTextContent('<script>');
  });

  it('omits the description context when the API supplies no description match', () => {
    render(<JobCard job={mockJob} />);
    expect(screen.queryByText('Matched in description:')).not.toBeInTheDocument();
  });
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

  it('provides a native detail destination for keyboard and modified-click navigation', () => {
    render(<JobCard job={mockJob} />);
    const detailLink = screen.getByRole('link', { name: /view details for/i });
    expect(detailLink.tagName).toBe('A');
    expect(detailLink).toHaveAttribute('href', `/jobs/${mockJob.id}`);
    expect(detailLink.tabIndex).toBe(0);
  });

  it('keeps Apply independently focusable without nested interactive links', () => {
    render(<JobCard job={mockJob} />);
    const detailLink = screen.getByRole('link', { name: /view details for/i });
    const applyLink = screen.getByRole('link', { name: /apply on company website/i });
    expect(detailLink).not.toContainElement(applyLink);
    expect(applyLink.closest('[role="link"]')).toBeNull();
    expect(applyLink.tabIndex).toBe(0);
    expect(screen.getAllByRole('link')).toHaveLength(2);
  });

  it('retains detail navigation when the external apply URL is unavailable', () => {
    render(<JobCard job={{ ...mockJob, canonical_url: '' }} />);
    expect(screen.getByRole('link', { name: /view details for/i })).toHaveAttribute('href', `/jobs/${mockJob.id}`);
    expect(screen.queryByRole('link', { name: /apply on company website/i })).not.toBeInTheDocument();
    expect(screen.getByText('Direct apply unavailable')).toBeInTheDocument();
  });
});
