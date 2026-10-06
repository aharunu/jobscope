import React from 'react';
import { render, screen, fireEvent, waitFor, within, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { JobFilters } from '../components/jobs/JobFilters';
import { ATS_TYPE_OPTIONS } from '../lib/constants';

const platforms = vi.hoisted(() => vi.fn());
vi.mock('../lib/api/sources', () => ({ listSourcePlatforms: platforms }));
beforeEach(() => { platforms.mockReset(); platforms.mockResolvedValue([]); });
afterEach(cleanup);

describe('JobFilters Component', () => {
  it('exposes every supported provider and emits the canonical ATS filter value', async () => {
    const onChange = vi.fn();
    render(<JobFilters filters={{}} onChange={onChange} onReset={vi.fn()} />);
    const select = screen.getByLabelText(/source platform/i);
    for (const option of ATS_TYPE_OPTIONS) expect(within(select).getByRole('option', { name: option.label })).toHaveValue(option.value);
    fireEvent.change(select, { target: { value: 'hirex' } });
    expect(onChange).toHaveBeenCalledWith({ ats_type: 'hirex' });
    fireEvent.change(select, { target: { value: '' } });
    expect(onChange).toHaveBeenLastCalledWith({ ats_type: undefined });
    await waitFor(() => expect(platforms).toHaveBeenCalledTimes(1));
  });

  it('refreshes registry platforms after returning to the page without duplicate options', async () => {
    platforms.mockResolvedValueOnce(['hirex']).mockResolvedValue(['hirex', 'kariyer_net', 'kariyer_net']);
    render(<JobFilters filters={{}} onChange={vi.fn()} onReset={vi.fn()} />);
    await waitFor(() => expect(platforms).toHaveBeenCalledTimes(1));
    fireEvent(window, new Event('focus'));
    expect(await screen.findByRole('option', { name: 'Kariyer.net' })).toHaveValue('kariyer_net');
    expect(screen.getAllByRole('option', { name: 'Hirex' })).toHaveLength(1);
  });

  it('retains selected and supported options when registry refresh fails', async () => {
    platforms.mockRejectedValue(new Error('Unavailable'));
    render(<JobFilters filters={{ ats_type: 'hirex' }} onChange={vi.fn()} onReset={vi.fn()} />);
    await screen.findByRole('status');
    expect(screen.getByLabelText(/source platform/i)).toHaveValue('hirex');
    expect(screen.getByRole('option', { name: 'Workday' })).toBeInTheDocument();
  });
  it('renders all filter controls and options', async () => {
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
    await waitFor(() => expect(platforms).toHaveBeenCalledTimes(1));
  });

  it('triggers onChange when selecting a work mode', async () => {
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
    await waitFor(() => expect(platforms).toHaveBeenCalledTimes(1));
  });

  it('displays Reset Filters button when active filters exist and invokes onReset', async () => {
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
    await waitFor(() => expect(platforms).toHaveBeenCalledTimes(1));
  });
});
