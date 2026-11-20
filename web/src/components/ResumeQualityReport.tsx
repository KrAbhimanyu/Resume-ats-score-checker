import React, { useState } from 'react';
import { Clipboard, ClipboardCheck, FileCheck2, Gauge, SpellCheck, Target } from 'lucide-react';
import { ResumeQualityReport as ResumeQualityReportData } from '../types/analysis';

interface ResumeQualityReportProps {
  report: ResumeQualityReportData;
}

const checkColor = (status: string): string =>
  status === 'pass' ? 'var(--color-success)' : 'var(--color-warning)';

export const ResumeQualityReport: React.FC<ResumeQualityReportProps> = ({ report }) => {
  const [copyError, setCopyError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const copySummary = async () => {
    try {
      await navigator.clipboard.writeText(report.professional_summary_draft);
      setCopied(true);
      setCopyError(null);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
      setCopyError('Could not access the clipboard. Select and copy the summary text instead.');
    }
  };

  return (
    <section className="quality-report-card" aria-labelledby="quality-report-title">
      <div className="quality-report-heading">
        <div>
          <span className="badge badge-primary">Local heuristic review</span>
          <h3 id="quality-report-title" className="section-title">Resume Quality & ATS Report</h3>
          <p>Specific checks and suggestions from extracted text—not a prediction of any employer’s ATS.</p>
        </div>
      </div>

      <div className="quality-score-grid">
        <article className="quality-score-tile">
          <Gauge size={19} aria-hidden="true" />
          <span>Readability</span>
          <strong>
            {report.readability_label === 'Not enough text' ? 'N/A' : `${report.readability_score}/100`}
          </strong>
          <small>{report.readability_label}</small>
        </article>
        <article className="quality-score-tile">
          <Target size={19} aria-hidden="true" />
          <span>Impact signals</span>
          <strong>{report.impact_score}/100</strong>
          <small>Evidence signals in achievement bullets</small>
        </article>
      </div>
      <p className="quality-explanation">{report.readability_explanation}</p>
      <p className="quality-explanation">{report.impact_explanation}</p>

      <div className="quality-report-columns">
        <section>
          <h4><FileCheck2 size={17} aria-hidden="true" /> Section-by-section review</h4>
          <div className="quality-check-list">
            {report.section_analysis.map((section) => (
              <article className="quality-check" key={section.name}>
                <div className="quality-check-title">
                  <strong>{section.name}</strong>
                  <span>{section.found ? `${section.word_count} words` : 'Not detected'}</span>
                </div>
                {section.findings.map((finding) => <p key={finding}>{finding}</p>)}
              </article>
            ))}
          </div>
          <h4 className="quality-subheading"><Target size={17} aria-hidden="true" /> ATS compatibility checks</h4>
          <div className="quality-check-list">
            {report.ats_compatibility_checks.map((check) => (
              <article className="quality-check" key={check.title}>
                <strong style={{ color: checkColor(check.status) }}>{check.title}</strong>
                <p>{check.detail}</p>
              </article>
            ))}
          </div>
        </section>

        <section>
          <h4><SpellCheck size={17} aria-hidden="true" /> Grammar & formatting review</h4>
          {report.grammar_issues.length ? (
            <div className="quality-check-list">
              {report.grammar_issues.map((issue, index) => (
                <article className="quality-check" key={`${issue.category}-${index}`}>
                  <strong>{issue.category}</strong>
                  <p><q>{issue.excerpt}</q> — {issue.suggestion}</p>
                </article>
              ))}
            </div>
          ) : (
            <p className="quality-explanation">No common grammar patterns were flagged. A human proofread is still recommended.</p>
          )}
          <ul className="quality-findings">
            {report.formatting_findings.map((finding) => <li key={finding}>{finding}</li>)}
          </ul>

          <h4 className="quality-subheading"><FileCheck2 size={17} aria-hidden="true" /> Final quality assurance</h4>
          <div className="quality-check-list">
            {report.quality_assurance_checks.map((check) => (
              <article className="quality-check" key={check.title}>
                <strong style={{ color: checkColor(check.status) }}>{check.title} · {check.status}</strong>
                <p>{check.detail}</p>
              </article>
            ))}
          </div>
        </section>
      </div>

      <div className="summary-draft-card">
        <div>
          <h4>Professional summary draft</h4>
          <p>Built from resume-detected skills. Verify every statement and tailor it before use.</p>
        </div>
        <blockquote>{report.professional_summary_draft}</blockquote>
        <button type="button" className="btn btn-secondary btn-small" onClick={copySummary}>
          {copied ? <ClipboardCheck size={15} /> : <Clipboard size={15} />}
          {copied ? 'Copied' : 'Copy summary'}
        </button>
        {copyError && <p className="quality-copy-error" role="alert">{copyError}</p>}
      </div>

      <p className="quality-disclaimer">
        Pattern-based checks can miss context or flag correct writing. Readability and impact scores are
        transparent heuristics; ATS layout checks cannot verify visual columns, tables, fonts, or graphics.
      </p>
    </section>
  );
};
