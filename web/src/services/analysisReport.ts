import { AnalysisResponse } from '../types/analysis';

const escapeHtml = (value: string): string =>
  value.replace(/[&<>"']/g, (character) => {
    const entities: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    };
    return entities[character];
  });

const listItems = (items: string[]): string =>
  items.length
    ? `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`
    : '<p>None reported.</p>';

export function buildAnalysisReportHtml(analysis: AnalysisResponse): string {
  const categories = analysis.category_scores
    .map(
      (category) =>
        `<tr><td>${escapeHtml(category.category_name)}</td><td>${category.score} / ${category.max_score}</td><td>${category.percentage}%</td><td>${escapeHtml(category.explanation)}</td></tr>`,
    )
    .join('');
  const quality = analysis.quality_report;
  const qualitySection = quality
    ? `<section><h2>Resume quality (separate from ATS match)</h2>
        <p>Readability estimate: ${quality.readability_label === 'Not enough text' ? 'Not scored' : `${quality.readability_score}/100`} — ${escapeHtml(quality.readability_label)}</p>
        <p>${escapeHtml(quality.readability_explanation)}</p>
        <p>Impact estimate: ${quality.impact_score}/100</p>
        <p>${escapeHtml(quality.impact_explanation)}</p>
        <h3>Section findings</h3>
        ${listItems(quality.section_analysis.flatMap((section) => section.findings.map((finding) => `${section.name}: ${finding}`)))}
        <h3>Formatting findings</h3>${listItems(quality.formatting_findings)}
        <h3>Possible grammar patterns for review</h3>
        ${listItems(quality.grammar_issues.map((issue) => `${issue.category}: ${issue.excerpt} — ${issue.suggestion}`))}
      </section>`
    : '';
  const bulletSuggestions = analysis.improvement_assistant?.bullet_improvements ?? [];
  const suggestionsSection = bulletSuggestions.length
    ? `<section><h2>Achievement statement suggestions</h2>
        ${bulletSuggestions
          .map(
            (bullet) =>
              `<article><h3>Original statement</h3><p>${escapeHtml(bullet.original_text)}</p>
                <h3>Suggested wording</h3><p>${escapeHtml(bullet.suggested_rewrite)}</p>
                <p>${escapeHtml(bullet.what_to_add)}</p></article>`,
          )
          .join('')}
        <p>Only retain claims, tools, and measurable outcomes you can verify.</p>
      </section>`
    : '';

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Resume ATS Analysis Report</title>
  <style>
    body{font:16px/1.55 system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#172033}
    h1,h2{color:#1e3a8a}section{border-top:1px solid #d5dbea;margin-top:2rem;padding-top:1rem}
    table{width:100%;border-collapse:collapse}th,td{text-align:left;border:1px solid #cbd5e1;padding:.55rem;vertical-align:top}
    .score{font-size:1.4rem;font-weight:700}.notice{background:#f1f5f9;padding:1rem}
  </style>
</head>
<body>
  <h1>Resume ATS Analysis Report</h1>
  <p>Document: ${escapeHtml(analysis.document_metadata.filename)} (${escapeHtml(analysis.document_metadata.file_type)}); ${analysis.document_metadata.word_count} extracted words.</p>
  <p class="score">${escapeHtml(analysis.score_label)}: ${analysis.overall_score}/100 — ${escapeHtml(analysis.match_tier)}</p>
  <p>${escapeHtml(analysis.summary)}</p>
  <section><h2>ATS match score breakdown</h2>
    <table><thead><tr><th>Category</th><th>Points</th><th>Percentage</th><th>Method details</th></tr></thead><tbody>${categories}</tbody></table>
  </section>
  <section><h2>Matched requirements</h2>${listItems(analysis.matched_requirements.map((item) => `${item.requirement} (${item.evidence_strength} evidence)`))}</section>
  <section><h2>Missing or weak requirements</h2>${listItems(analysis.missing_requirements.map((item) => `${item.requirement}: ${item.reason}`))}</section>
  <section><h2>Recommendations</h2>${listItems(analysis.recommendations.map((item) => `${item.title}: ${item.description}`))}</section>
  ${qualitySection}
  ${suggestionsSection}
  <section><h2>Extraction warnings</h2>${listItems(analysis.document_metadata.extraction_warnings)}</section>
  <p class="notice">${escapeHtml(analysis.limitations_disclaimer)}</p>
</body>
</html>`;
}

export function downloadAnalysisReport(analysis: AnalysisResponse): void {
  const report = new Blob([buildAnalysisReportHtml(analysis)], { type: 'text/html;charset=utf-8' });
  const objectUrl = URL.createObjectURL(report);
  const link = document.createElement('a');
  const baseName = analysis.document_metadata.filename
    .replace(/\.[^.]+$/, '')
    .replace(/[^\w-]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'resume';
  link.href = objectUrl;
  link.download = `${baseName}_analysis_report.html`;
  link.style.display = 'none';
  document.body.appendChild(link);
  try {
    link.click();
  } finally {
    link.remove();
    URL.revokeObjectURL(objectUrl);
  }
}
