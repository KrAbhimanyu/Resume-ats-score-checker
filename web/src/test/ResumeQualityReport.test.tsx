import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ResumeQualityReport } from '../components/ResumeQualityReport';
import { ResumeQualityReport as ResumeQualityReportData } from '../types/analysis';

const report: ResumeQualityReportData = {
  section_analysis: [
    { name: 'Experience', found: true, word_count: 32, findings: ['Add verified metrics where available.'] },
  ],
  formatting_findings: ['Use recognizable section headings.'],
  grammar_issues: [
    { category: 'Repeated word', excerpt: 'the the', suggestion: 'Check the duplicate.' },
  ],
  readability_score: 72.4,
  readability_label: 'Generally easy to read',
  readability_explanation: 'Estimated from the extracted text.',
  impact_score: 50,
  impact_explanation: 'One of two bullets contains a numeric signal.',
  ats_compatibility_checks: [
    { title: 'Standard section headings', status: 'pass', detail: 'Three headings detected.' },
  ],
  quality_assurance_checks: [
    { title: 'Grammar pattern review', status: 'attention', detail: 'Review flagged text.' },
  ],
  professional_summary_draft: 'Professional with resume-documented experience in Python.',
};

describe('ResumeQualityReport', () => {
  it('renders scores, writing checks, ATS checks, and summary guidance', () => {
    render(<ResumeQualityReport report={report} />);

    expect(screen.getByText('72.4/100')).toBeInTheDocument();
    expect(screen.getByText('50/100')).toBeInTheDocument();
    expect(screen.getByText('Add verified metrics where available.')).toBeInTheDocument();
    expect(screen.getByText('the the')).toBeInTheDocument();
    expect(screen.getByText('Standard section headings')).toBeInTheDocument();
    expect(screen.getByText(report.professional_summary_draft)).toBeInTheDocument();
  });

  it('surfaces clipboard failures instead of silently ignoring them', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('clipboard unavailable'));
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });
    render(<ResumeQualityReport report={report} />);

    fireEvent.click(screen.getByRole('button', { name: /copy summary/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/select and copy/i);
  });

  it('does not present a withheld readability estimate as a zero score', () => {
    render(
      <ResumeQualityReport
        report={{ ...report, readability_score: 0, readability_label: 'Not enough text' }}
      />,
    );

    expect(screen.getByText('N/A')).toBeInTheDocument();
    expect(screen.queryByText('0/100')).not.toBeInTheDocument();
  });
});
