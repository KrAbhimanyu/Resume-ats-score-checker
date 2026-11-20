import { afterEach, describe, expect, it, vi } from 'vitest';
import { AnalysisResponse } from '../types/analysis';
import { buildAnalysisReportHtml, downloadAnalysisReport } from '../services/analysisReport';

const analysis: AnalysisResponse = {
  overall_score: 72,
  score_label: 'Estimated Resume–Job Match Score',
  match_tier: 'Strong Match',
  summary: 'A report for <Jordan>.',
  category_scores: [
    {
      category_id: 'document_structure',
      category_name: 'Document structure',
      score: 7,
      max_score: 10,
      percentage: 70,
      explanation: 'Three sections detected.',
      details: {},
    },
  ],
  matched_requirements: [],
  missing_requirements: [],
  keywords_found: [],
  recommendations: [],
  document_metadata: {
    filename: 'Jordan Resume.pdf',
    file_type: '.pdf',
    file_size_bytes: 1200,
    character_count: 600,
    word_count: 100,
    extraction_warnings: ['Review <column> ordering.'],
  },
  limitations_disclaimer: 'Heuristic estimate only.',
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe('analysis report download', () => {
  it('builds a readable report and escapes resume-derived text', () => {
    const html = buildAnalysisReportHtml(analysis);

    expect(html).toContain('Estimated Resume–Job Match Score: 72/100');
    expect(html).toContain('A report for &lt;Jordan&gt;.');
    expect(html).toContain('Review &lt;column&gt; ordering.');
    expect(html).not.toContain('A report for <Jordan>.');
  });

  it('labels withheld readability estimates as not scored', () => {
    const html = buildAnalysisReportHtml({
      ...analysis,
      quality_report: {
        section_analysis: [],
        formatting_findings: [],
        grammar_issues: [],
        readability_score: 0,
        readability_label: 'Not enough text',
        readability_explanation: 'Estimate withheld.',
        impact_score: 0,
        impact_explanation: 'No achievement evidence.',
        ats_compatibility_checks: [],
        quality_assurance_checks: [],
        professional_summary_draft: 'No draft.',
      },
    });

    expect(html).toContain('Readability estimate: Not scored — Not enough text');
    expect(html).not.toContain('Readability estimate: 0/100');
  });

  it('triggers a browser download and releases the generated object URL', () => {
    const createObjectURL = vi.fn().mockReturnValue('blob:analysis-report');
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);

    downloadAnalysisReport(analysis);

    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(click).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:analysis-report');
  });
});
