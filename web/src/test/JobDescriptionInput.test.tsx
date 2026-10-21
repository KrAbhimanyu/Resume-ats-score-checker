import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { JobDescriptionInput } from '../components/JobDescriptionInput';

describe('JobDescriptionInput Component', () => {
  it('renders textarea with proper labels', () => {
    const handleChange = vi.fn();
    render(<JobDescriptionInput value="" onChange={handleChange} />);

    expect(screen.getByLabelText(/Job Description/i)).toBeInTheDocument();
    expect(screen.getByText(/0 words \(0 characters\)/i)).toBeInTheDocument();
  });

  it('updates word and character count correctly on change', () => {
    const handleChange = vi.fn();
    const text = 'Senior Software Engineer with Python and FastAPI experience';
    const { rerender } = render(<JobDescriptionInput value="" onChange={handleChange} />);

    const textarea = screen.getByLabelText(/Job Description/i);
    fireEvent.change(textarea, { target: { value: text } });

    expect(handleChange).toHaveBeenCalledWith(text);

    rerender(<JobDescriptionInput value={text} onChange={handleChange} />);
    expect(screen.getByText(/8 words \(59 characters\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Sufficient detail/i)).toBeInTheDocument();
  });

  it('displays validation error message when passed', () => {
    const handleChange = vi.fn();
    render(
      <JobDescriptionInput
        value=""
        onChange={handleChange}
        error="Job description contains insufficient content."
      />
    );

    expect(screen.getByText(/Job description contains insufficient content/i)).toBeInTheDocument();
  });
});

