import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ResumeVersionWorkspace } from '../components/ResumeVersionWorkspace';
import { StructuredResume } from '../types/builder';

const resume: StructuredResume = {
  contact_info: { full_name: 'Alex Example' },
  summary: 'Backend engineer.',
  skills: { Languages: ['Python'] },
  experience: [],
  projects: [],
  education: [],
  certifications: [],
};

describe('ResumeVersionWorkspace', () => {
  it('saves versions locally, compares them, restores and exports a snapshot', async () => {
    window.localStorage.clear();
    const onRestore = vi.fn();
    const onExport = vi.fn();
    const props = {
      resume,
      targetRole: 'Backend Engineer',
      targetCompany: 'Example',
      onRestore,
      onExport,
    };
    const { rerender } = render(<ResumeVersionWorkspace {...props} />);

    fireEvent.change(screen.getByLabelText('Version name'), { target: { value: 'Original' } });
    fireEvent.click(screen.getByRole('button', { name: /save current version/i }));
    expect(await screen.findByText('Saved “Original” in this browser.')).toBeInTheDocument();

    rerender(
      <ResumeVersionWorkspace
        {...props}
        resume={{ ...resume, summary: 'Backend engineer improving reliable APIs.' }}
      />
    );
    fireEvent.change(screen.getByLabelText('Version name'), { target: { value: 'Updated' } });
    fireEvent.click(screen.getByRole('button', { name: /save current version/i }));
    expect(await screen.findByText('Saved “Updated” in this browser.')).toBeInTheDocument();

    const stored = JSON.parse(window.localStorage.getItem('resume-ats-checker:resume-versions:v1') || '[]') as Array<{ id: string; name: string }>;
    const older = stored.find((version) => version.name === 'Original');
    const newer = stored.find((version) => version.name === 'Updated');
    expect(older).toBeDefined();
    expect(newer).toBeDefined();

    fireEvent.change(screen.getByLabelText('Older version'), { target: { value: older?.id } });
    fireEvent.change(screen.getByLabelText('Newer version'), { target: { value: newer?.id } });
    expect(await screen.findByText('Professional summary changed')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /export original as pdf/i }));
    expect(onExport).toHaveBeenCalledWith(resume, 'pdf', 'Example');

    fireEvent.click(screen.getAllByRole('button', { name: 'Restore' })[0]);
    expect(onRestore).toHaveBeenCalled();
  });
});
