import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { JobSearchInput } from '../components/jobs/JobSearchInput';

describe('JobSearchInput', () => {
  it('explains exact search and preserves quotes in the debounced query', async () => {
    const onChange = vi.fn();
    render(<JobSearchInput value="" onChange={onChange} />);
    const input = screen.getByRole('textbox', { name: /search jobs/i });

    expect(input).toHaveAccessibleDescription(/double quotes.*intern/i);
    fireEvent.change(input, { target: { value: '"intern"' } });
    expect(onChange).not.toHaveBeenCalled();
    await waitFor(() => expect(onChange).toHaveBeenCalledWith('"intern"'));
    expect(onChange).toHaveBeenCalledTimes(1);
  });
});
