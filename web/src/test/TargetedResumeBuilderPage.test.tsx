import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TargetedResumeBuilderPage } from '../pages/TargetedResumeBuilderPage';
import * as analysisApi from '../services/analysisApi';
import { TargetedAnalysisResponse } from '../types/builder';

const mockTargetedResponse: TargetedAnalysisResponse = {
  target_mode: 'faang_big_tech',
  company_name: 'Google',
  job_title: 'Software Engineer',
  has_job_description: true,
  guidance_source: 'Actual Job Description (Primary Source)',
  summary_overview: 'Tailored analysis for Software Engineer at Google.',
  matched_skills: [
    {
      name: 'python',
      category: 'skill',
      status: 'matched',
      reason: "Skill 'python' is evidenced in work experience.",
      evidence_source: 'Job Description',
      actionable_guidance: 'Maintain quantifiable metrics.',
      requires_user_confirmation: false,
    },
  ],
  missing_requirements: [
    {
      name: 'kubernetes',
      category: 'skill',
      status: 'missing',
      reason: "Skill 'kubernetes' is expected at Google.",
      evidence_source: 'Job Description',
      actionable_guidance: 'Confirm if you have genuine experience.',
      requires_user_confirmation: true,
    },
  ],
  weakly_evidenced: [
    {
      name: 'react',
      category: 'skill',
      status: 'weakly_evidenced',
      reason: "Skill 'react' is listed in skills but lacks project bullets.",
      evidence_source: 'Job Description',
      actionable_guidance: 'Add a project accomplishment bullet.',
      requires_user_confirmation: false,
    },
  ],
  structure_feedback: ['Professional Summary is well-targeted.'],
  prioritized_improvements: [
    {
      id: 'imp-1',
      title: 'Review missing qualifications: kubernetes',
      priority: 'high',
      reason: 'Essential requirement for Google.',
      requires_confirmation: true,
    },
  ],
  proposed_changes: [
    {
      id: 'pc-1',
      section: 'summary',
      original_text: 'Experienced software developer.',
      proposed_text: 'Targeted Software Engineer with expertise in Python and distributed systems, achieving [add verified result].',
      rationale: 'Directly aligns with Google software engineering expectations.',
      evidence_source: 'Job Description',
      what_to_verify: 'Replace [add verified result] with a verified metric.',
      is_accepted: true,
    },
    {
      id: 'pc-2',
      section: 'experience',
      target_item_id: 'exp-1',
      bullet_index: 0,
      original_text: 'Worked on REST API services.',
      proposed_text: 'Engineered high-throughput REST APIs using Python and PostgreSQL, achieving [add verified result].',
      rationale: "Replaces passive 'worked on' with active verb.",
      evidence_source: 'Job Description',
      what_to_verify: 'Verify query speedup or latency reduced.',
      is_accepted: true,
    },
  ],
  draft_resume: {
    contact_info: {
      full_name: 'Alex Morgan',
      email: 'alex@example.com',
      phone: '555-0100',
      location: 'Seattle, WA',
      linkedin: 'linkedin.com/in/alexmorgan',
    },
    summary: 'Experienced software developer.',
    skills: {
      Languages: ['Python', 'SQL'],
      'Frameworks & Libraries': ['FastAPI', 'React'],
    },
    experience: [
      {
        id: 'exp-1',
        title: 'Software Engineer',
        company: 'CloudTech',
        start_date: '2021',
        end_date: 'Present',
        bullets: ['Worked on REST API services.'],
      },
    ],
    projects: [],
    education: [
      {
        id: 'edu-1',
        degree: 'B.S. in Computer Science',
        institution: 'University of Washington',
        graduation_date: '2021',
      },
    ],
    certifications: [],
  },
  disclaimer: 'Company-specific guidance is compiled from general public culture insights.',
};

describe('TargetedResumeBuilderPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Step 1 with FAANG/Big Tech and Any Company tabs', () => {
    render(<TargetedResumeBuilderPage />);

    expect(screen.getByText('Targeted Resume Builder')).toBeInTheDocument();
    expect(screen.getByText('1. Configure Your Target Company & Role')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /FAANG \/ Big Tech/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Any Company/i })).toBeInTheDocument();
    expect(screen.getByText('Google')).toBeInTheDocument();
    expect(screen.getByText('Amazon')).toBeInTheDocument();
  });

  it('switches between FAANG and Any Company modes', () => {
    render(<TargetedResumeBuilderPage />);

    const anyCompanyTab = screen.getByRole('tab', { name: /Any Company/i });
    fireEvent.click(anyCompanyTab);

    expect(screen.getByLabelText(/Target Company Name \*/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Industry \(Optional\)/i)).toBeInTheDocument();
  });

  it('validates required inputs before submitting', () => {
    render(<TargetedResumeBuilderPage />);

    const analyzeBtn = screen.getByRole('button', { name: /Analyze & Build Targeted Resume/i });
    fireEvent.click(analyzeBtn);

    expect(screen.getByText(/Please upload your existing resume/i)).toBeInTheDocument();
  });

  it('analyzes resume, transitions to Step 2, and renders gap analysis', async () => {
    const mockAnalyzeAndPlan = vi
      .spyOn(analysisApi, 'analyzeAndPlanTargetedResume')
      .mockResolvedValueOnce(mockTargetedResponse);

    render(<TargetedResumeBuilderPage />);

    // Mock file input
    const file = new File(['%PDF-1.4 dummy content'], 'resume.pdf', { type: 'application/pdf' });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    if (fileInput) {
      fireEvent.change(fileInput, { target: { files: [file] } });
    }

    const analyzeBtn = screen.getByRole('button', { name: /Analyze & Build Targeted Resume/i });
    fireEvent.click(analyzeBtn);

    await waitFor(() => {
      expect(mockAnalyzeAndPlan).toHaveBeenCalled();
    });

    // Step 2 should now be visible
    expect(await screen.findByText(/Target Requirement Gap Analysis/i)).toBeInTheDocument();
    expect(screen.getByText('python')).toBeInTheDocument();
    expect(screen.getByText('kubernetes')).toBeInTheDocument();
    expect(screen.getByText('react')).toBeInTheDocument();
    expect(screen.getByText(/Proposed Targeted Rewrites/i)).toBeInTheDocument();
  });

  it('allows user to toggle accept/reject and edit proposed rewrites', async () => {
    vi.spyOn(analysisApi, 'analyzeAndPlanTargetedResume').mockResolvedValueOnce(mockTargetedResponse);

    render(<TargetedResumeBuilderPage />);

    const file = new File(['%PDF-1.4 dummy content'], 'resume.pdf', { type: 'application/pdf' });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    if (fileInput) {
      fireEvent.change(fileInput, { target: { files: [file] } });
    }

    fireEvent.click(screen.getByRole('button', { name: /Analyze & Build Targeted Resume/i }));

    // Wait for Step 2
    expect(await screen.findByText(/Proposed Targeted Rewrites/i)).toBeInTheDocument();

    // Toggle accept on second item
    const approvedBtns = screen.getAllByRole('button', { name: /Approved/i });
    expect(approvedBtns.length).toBe(2);

    fireEvent.click(approvedBtns[1]);
    expect(screen.getByRole('button', { name: /Rejected/i })).toBeInTheDocument();

    // Click edit on first change
    const editBtns = screen.getAllByRole('button', { name: /Edit Suggestion/i });
    fireEvent.click(editBtns[0]);

    const textarea = screen.getByDisplayValue(mockTargetedResponse.proposed_changes[0].proposed_text);
    fireEvent.change(textarea, {
      target: { value: 'Targeted Software Engineer with expertise in Python, achieving 40% latency reduction.' },
    });

    const saveBtn = screen.getByRole('button', { name: /Save Edit/i });
    fireEvent.click(saveBtn);

    expect(screen.getByText(/achieving 40% latency reduction/)).toBeInTheDocument();
  });

  it('proceeds to Step 3 (Preview & Export) and handles PDF export', async () => {
    vi.spyOn(analysisApi, 'analyzeAndPlanTargetedResume').mockResolvedValueOnce(mockTargetedResponse);
    const mockExportResume = vi.spyOn(analysisApi, 'exportResume').mockResolvedValueOnce(new Blob(['pdf content'], { type: 'application/pdf' }));

    // Mock URL.createObjectURL
    window.URL.createObjectURL = vi.fn().mockReturnValue('blob:mock-url');
    window.URL.revokeObjectURL = vi.fn();

    render(<TargetedResumeBuilderPage />);

    const file = new File(['%PDF-1.4 dummy content'], 'resume.pdf', { type: 'application/pdf' });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    if (fileInput) {
      fireEvent.change(fileInput, { target: { files: [file] } });
    }

    fireEvent.click(screen.getByRole('button', { name: /Analyze & Build Targeted Resume/i }));

    // Wait for Step 2 and proceed to preview
    const previewBtn = await screen.findByRole('button', { name: /Apply & Preview Resume/i });
    fireEvent.click(previewBtn);

    // Step 3 preview is rendered
    expect(await screen.findByText('Alex Morgan')).toBeInTheDocument();
    expect(screen.getByText('CloudTech')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Export PDF/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Export DOCX/i })).toBeInTheDocument();

    // Click export PDF
    fireEvent.click(screen.getByRole('button', { name: /Export PDF/i }));

    await waitFor(() => {
      expect(mockExportResume).toHaveBeenCalledWith(expect.any(Object), 'pdf', expect.any(String));
    });

    expect(await screen.findByText(/Successfully exported your resume to PDF/i)).toBeInTheDocument();
  });
});

