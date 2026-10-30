import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ResumeImprovementDashboard } from '../components/ResumeImprovementDashboard';
import { ResumeImprovementAssistant } from '../types/analysis';
import * as analysisApi from '../services/analysisApi';

const mockAssistant: ResumeImprovementAssistant = {
  strengths: [
    {
      title: 'Strong Action Verb Usage',
      description: 'Detected 6 assertive action verbs (e.g., Architected, Reduced).',
      category: 'clarity',
    },
    {
      title: 'Evidence of Quantifiable Impact',
      description: 'Included 3 measurable performance indicators (35%, 100k daily users).',
      category: 'metrics',
    },
  ],
  bullet_improvements: [
    {
      id: 'bi-1',
      original_text: 'Worked on API testing.',
      issue: "Starts with passive phrasing 'worked on' instead of a decisive action verb; lacks quantifiable metrics.",
      suggested_rewrite: 'Tested REST APIs using Postman, achieving [add verified result, e.g., 99% pass rate].',
      what_to_add: 'Add specific testing tools and verified outcome metrics.',
      action_verb: 'Tested',
      detected_skills: ['rest api'],
    },
    {
      id: 'bi-2',
      original_text: 'Responsible for Docker deployments.',
      issue: "Uses job-duty phrasing ('responsible for') rather than an accomplishment statement.",
      suggested_rewrite: 'Orchestrated container deployments utilizing Docker, achieving [add verified result].',
      what_to_add: 'Add production deployment metrics or frequency.',
      action_verb: 'Orchestrated',
      detected_skills: ['docker'],
    },
  ],
  skill_alignment: {
    matched_skills: ['python', 'fastapi', 'docker'],
    missing_from_resume_skills: ['kubernetes', 'aws'],
    weakly_evidenced_skills: ['react'],
    ethical_guidance: 'Important: Only add skills and experiences you truthfully possess.',
  },
  recommended_verbs: [
    {
      category_name: 'Technical & Architecture',
      verbs: ['Architected', 'Engineered', 'Automated'],
    },
    {
      category_name: 'Leadership & Ownership',
      verbs: ['Spearheaded', 'Orchestrated'],
    },
  ],
  metric_guidance: [
    {
      metric_type: 'Scale & Traffic',
      guiding_question: 'How many daily active users did this service support?',
      example_pattern: 'Scaled service to handle [add verified count, e.g., 50k users].',
    },
  ],
  improvement_checklist: [
    {
      id: 'chk-1',
      title: 'Review missing job skills: kubernetes, aws',
      description: 'Evaluate whether you have hands-on experience.',
      priority: 'high',
      completed: false,
    },
    {
      id: 'chk-2',
      title: 'Upgrade 2 weak resume bullet points',
      description: 'Convert passive phrases into Action + Task + Method + [Result].',
      priority: 'high',
      completed: false,
    },
    {
      id: 'chk-3',
      title: 'Final formatting check',
      description: 'Check single-column layout.',
      priority: 'low',
      completed: false,
    },
  ],
};

describe('ResumeImprovementDashboard Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock navigator.clipboard
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockImplementation(() => Promise.resolve()),
      },
    });
  });

  it('renders strengths, weak bullets, skill alignment, and checklist', () => {
    render(<ResumeImprovementDashboard assistant={mockAssistant} />);

    // Strengths
    expect(screen.getByText('Resume Improvement Assistant')).toBeInTheDocument();
    expect(screen.getByText('Strong Action Verb Usage')).toBeInTheDocument();
    expect(screen.getByText('Evidence of Quantifiable Impact')).toBeInTheDocument();

    // Bullet points
    expect(screen.getByText(/"Worked on API testing."/)).toBeInTheDocument();
    expect(screen.getByText(/Tested REST APIs using Postman/)).toBeInTheDocument();
    expect(screen.getAllByText(/\[add verified result/).length).toBeGreaterThan(0);

    // Skill Alignment
    expect(screen.getByText(/Skills Found in Both Resume & Job/)).toBeInTheDocument();
    expect(screen.getByText('python')).toBeInTheDocument();
    expect(screen.getByText('kubernetes')).toBeInTheDocument();
    expect(screen.getByText('react')).toBeInTheDocument();
    expect(screen.getByText(/Only add skills and experiences you truthfully possess/)).toBeInTheDocument();

    // Checklist
    expect(screen.getByText(/Review missing job skills: kubernetes, aws/)).toBeInTheDocument();
    expect(screen.getByText('0 of 3 completed (0%)')).toBeInTheDocument();
  });

  it('allows user to edit a suggested rewrite inline before copying', () => {
    render(<ResumeImprovementDashboard assistant={mockAssistant} />);

    const editBtns = screen.getAllByRole('button', { name: /Edit Suggestion/i });
    expect(editBtns.length).toBeGreaterThan(0);

    // Click edit on first bullet
    fireEvent.click(editBtns[0]);

    // Should now show textarea
    const textarea = screen.getByLabelText(/Edit suggested rewrite/i);
    expect(textarea).toBeInTheDocument();

    // User replaces placeholder with real verified result
    fireEvent.change(textarea, {
      target: { value: 'Tested REST APIs using Postman, achieving 99.8% test pass rate with 0 regressions.' },
    });

    // Click Done Editing
    const doneBtn = screen.getByRole('button', { name: /Done Editing/i });
    fireEvent.click(doneBtn);

    // Should display edited version
    expect(
      screen.getByText('Tested REST APIs using Postman, achieving 99.8% test pass rate with 0 regressions.')
    ).toBeInTheDocument();
  });

  it('allows user to copy the rewrite and displays Copied state', async () => {
    render(<ResumeImprovementDashboard assistant={mockAssistant} />);

    const copyBtns = screen.getAllByRole('button', { name: /Copy Suggested Rewrite/i });
    expect(copyBtns.length).toBeGreaterThan(0);

    fireEvent.click(copyBtns[0]);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      'Tested REST APIs using Postman, achieving [add verified result, e.g., 99% pass rate].'
    );

    // Visual feedback
    await waitFor(() => {
      expect(screen.getByText('Copied!')).toBeInTheDocument();
    });
  });

  it('toggles checklist items and updates progress counter and bar', () => {
    render(<ResumeImprovementDashboard assistant={mockAssistant} />);

    expect(screen.getByText('0 of 3 completed (0%)')).toBeInTheDocument();

    // Check first checkbox
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBe(3);

    fireEvent.click(checkboxes[0]);
    expect(screen.getByText('1 of 3 completed (33%)')).toBeInTheDocument();

    fireEvent.click(checkboxes[1]);
    expect(screen.getByText('2 of 3 completed (67%)')).toBeInTheDocument();

    // Uncheck first
    fireEvent.click(checkboxes[0]);
    expect(screen.getByText('1 of 3 completed (33%)')).toBeInTheDocument();
  });

  it('allows analyzing and editing a custom bullet point through the interactive tester', async () => {
    const mockImproveBullet = vi.spyOn(analysisApi, 'improveBullet').mockResolvedValueOnce({
      original_text: 'Assisted with database queries.',
      is_weak: true,
      issues: ["Starts with passive phrasing 'assisted with'."],
      suggested_rewrite: 'Optimized complex database queries utilizing SQL, achieving [add verified result].',
      what_to_add: 'Provide database name and verified query speedup.',
      recommended_action_verbs: ['Optimized', 'Engineered'],
    });

    render(<ResumeImprovementDashboard assistant={mockAssistant} />);

    const input = screen.getByLabelText(/Custom bullet point input/i);
    const analyzeBtn = screen.getByRole('button', { name: /Analyze Bullet Point/i });

    fireEvent.change(input, { target: { value: 'Assisted with database queries.' } });
    fireEvent.click(analyzeBtn);

    await waitFor(() => {
      expect(mockImproveBullet).toHaveBeenCalledWith('Assisted with database queries.', ['python', 'fastapi', 'docker']);
    });

    expect(await screen.findByText(/Optimized complex database queries utilizing SQL/)).toBeInTheDocument();
  });
});
