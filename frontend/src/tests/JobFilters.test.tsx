import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { JobFilters } from '../components/jobs/JobFilters';

describe('JobFilters Component', () => {
  it('renders all filter controls and options', () => {
    const handleChange = vi.fn();
    const handleReset = vi.fn();

    render(
      <JobFilters
        filters={{}}
        onChange={handleChange}
        onReset={handleReset}
      />
    );

    expect(screen.getByLabelText(/status/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/work mode/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/employment type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/source platform/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/filter by company/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/filter by location/i)).toBeInTheDocument();
  });

  it('triggers onChange when selecting a work mode', () => {
    const handleChange = vi.fn();
    const handleReset = vi.fn();

    render(
      <JobFilters
        filters={{}}
        onChange={handleChange}
        onReset={handleReset}
      />
    );

    const workModeSelect = screen.getByLabelText(/work mode/i);
    fireEvent.change(workModeSelect, { target: { value: 'Remote' } });

    expect(handleChange).toHaveBeenCalledWith({ work_mode: 'Remote' });
  });

  it('displays Reset Filters button when active filters exist and invokes onReset', () => {
    const handleChange = vi.fn();
    const handleReset = vi.fn();

    render(
      <JobFilters
        filters={{ work_mode: 'Remote' }}
        onChange={handleChange}
        onReset={handleReset}
      />
    );

    const resetButton = screen.getByRole('button', { name: /reset filters/i });
    expect(resetButton).toBeInTheDocument();

    fireEvent.click(resetButton);
    expect(handleReset).toHaveBeenCalledTimes(1);
  });
});
