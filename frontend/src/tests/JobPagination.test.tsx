import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { JobPagination } from '../components/jobs/JobPagination';

describe('JobPagination Component', () => {
  it('renders record range and page information accurately', () => {
    const handlePageChange = vi.fn();
    const handleLimitChange = vi.fn();

    render(
      <JobPagination
        total={120}
        limit={50}
        offset={0}
        onPageChange={handlePageChange}
        onLimitChange={handleLimitChange}
      />
    );

    expect(screen.getByText('Page 1 of 3')).toBeInTheDocument();
    expect(screen.getByText(/showing/i)).toHaveTextContent('Showing 1–50 of 120 jobs');
  });

  it('disables previous button on first page and enables next button', () => {
    const handlePageChange = vi.fn();
    const handleLimitChange = vi.fn();

    render(
      <JobPagination
        total={120}
        limit={50}
        offset={0}
        onPageChange={handlePageChange}
        onLimitChange={handleLimitChange}
      />
    );

    const prevButton = screen.getByRole('button', { name: /previous page/i });
    const nextButton = screen.getByRole('button', { name: /next page/i });

    expect(prevButton).toBeDisabled();
    expect(nextButton).not.toBeDisabled();

    fireEvent.click(nextButton);
    expect(handlePageChange).toHaveBeenCalledWith(50);
  });
});
