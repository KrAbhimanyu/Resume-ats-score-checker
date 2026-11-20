import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ResumeStudioPage } from '../pages/ResumeStudioPage';
import { RESUME_TEMPLATES } from '../services/resumeStudio';

describe('ResumeStudioPage', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it('builds a draft, exposes the template catalog and custom sections, and saves local profiles', async () => {
    render(<ResumeStudioPage />);
    expect(screen.getByRole('heading', { name: /build, tailor, and manage your resume/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /ATS-friendly templates/i })).toHaveTextContent(
      String(RESUME_TEMPLATES.length),
    );
    fireEvent.change(screen.getByLabelText('Filter by industry'), { target: { value: 'Healthcare' } });
    expect(screen.getByRole('button', { name: /Healthcare Navy/ })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Full name'), { target: { value: 'Alex Example' } });
    fireEvent.change(screen.getByLabelText('Custom section title'), { target: { value: 'Publications' } });
    fireEvent.click(screen.getByRole('button', { name: /add section/i }));
    expect(screen.getByLabelText('Publications entries')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Profile name'), { target: { value: 'Research CV' } });
    fireEvent.click(screen.getByRole('button', { name: /save profile/i }));
    expect(await screen.findByText(/Saved “Research CV” on this device/i)).toBeInTheDocument();
    expect(window.localStorage.getItem('resume-ats-checker:studio-profiles:v1')).toContain('Research CV');
  });

  it('generates editable companion documents, applies local tailoring, and explains translation limits', async () => {
    render(<ResumeStudioPage />);
    fireEvent.change(screen.getByLabelText('Full name'), { target: { value: 'Alex Example' } });
    fireEvent.change(screen.getByLabelText(/Skills \(one per line\)/), {
      target: { value: 'Python\nSQL' },
    });
    fireEvent.change(screen.getAllByLabelText('Target role')[0], { target: { value: 'Analyst' } });
    fireEvent.change(screen.getByLabelText('Job description'), {
      target: { value: 'Seeking analyst with SQL experience and Python reporting.' },
    });
    fireEvent.click(screen.getByRole('button', { name: /tailor existing content/i }));
    expect(await screen.findByText(/No skills, experience, or metrics were added/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Company'), { target: { value: 'Example Corp' } });
    fireEvent.click(screen.getByRole('button', { name: /generate document drafts/i }));
    await waitFor(() => {
      expect((screen.getByLabelText('Cover letter') as HTMLTextAreaElement).value).toContain('Example Corp Hiring Team');
      expect((screen.getByLabelText(/LinkedIn headline and About draft/i) as HTMLTextAreaElement).value).toContain('HEADLINE');
    });
    expect(screen.getByText(/Translation is unavailable in local-only mode/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /translate resume unavailable/i })).toBeDisabled();
  });
});
