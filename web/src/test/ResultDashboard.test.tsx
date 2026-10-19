import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ScoreOverview } from '../components/ScoreOverview';
import { CategoryBreakdown } from '../components/CategoryBreakdown';
import { KeywordAnalysis } from '../components/KeywordAnalysis';
import { RecommendationsList } from '../components/RecommendationsList';
import { AnalysisResponse } from '../types/analysis';

const mockResponse: AnalysisResponse = {
  overall_score: 78.5,
  score_label: 'Estimated Resume–Job Match Score',
  match_tier: 'Strong Match',
  summary: 'Your resume achieved an Estimated Resume–Job Match Score of 78.5/100 (Strong Match).',
  category_scores: [
    {
      category_id: 'keyword_coverage',
      category_name: 'Job-Relevant Keyword Coverage',
      score: 28.0,
      max_score: 35.0,
      percentage: 80.0,
      explanation: 'Matched 8 of 10 keywords from job description.',
      details: {},
    },
    {
      category_id: 'skills_match',
      category_name: 'Required and Preferred Skills Match',
      score: 20.0,
      max_score: 25.0,
      percentage: 80.0,
      explanation: 'Matched core skills: Python, React, PostgreSQL.',
      details: {},
    },
  ],
  matched_requirements: [
    {
      requirement: 'Experience with Python and FastAPI',
      category: 'skill',
      matched_terms: ['python', 'fastapi'],
      evidence_strength: 'strong',
      is_mandatory: true,
    },
  ],
  missing_requirements: [
    {
      requirement: 'Kubernetes container orchestration',
      category: 'skill',
      importance: 'mandatory',
      reason: 'Skill not evidenced in resume.',
      is_evidenced_elsewhere: false,
    },
    {
      requirement: 'AWS Cloud Deployment',
      category: 'experience',
      importance: 'preferred',
      reason: 'Mentioned briefly but lacks project evidence.',
      is_evidenced_elsewhere: true,
    },
  ],
  keywords_found: ['python', 'fastapi', 'react', 'postgresql', 'docker'],
  recommendations: [
    {
      id: 'rec-1',
      category: 'skills',
      title: 'Address Missing Core Skill: Kubernetes',
      description: 'Highlight container orchestration tools you have worked with.',
      action_type: 'add_missing_keyword',
      priority: 'high',
    },
  ],
  document_metadata: {
    filename: 'alex_morgan_resume.pdf',
    file_type: '.pdf',
    file_size_bytes: 4096,
    character_count: 900,
    word_count: 145,
    extraction_warnings: [],
  },
  limitations_disclaimer:
    'This score is an Estimated Resume–Job Match Score calculated via deterministic heuristic analysis.',
};

describe('Results Dashboard Components', () => {
  it('renders ScoreOverview with score, label, and tier', () => {
    const handleReset = vi.fn();
    render(
      <ScoreOverview
        score={mockResponse.overall_score}
        scoreLabel={mockResponse.score_label}
        matchTier={mockResponse.match_tier}
        summary={mockResponse.summary}
        onReset={handleReset}
      />
    );

    expect(screen.getByText('79')).toBeInTheDocument(); // Math.round(78.5)
    expect(screen.getByText('/100')).toBeInTheDocument();
    expect(screen.getByText('Estimated Resume–Job Match Score')).toBeInTheDocument();
    expect(screen.getByText('Strong Match')).toBeInTheDocument();

    const resetBtn = screen.getByRole('button', { name: /Analyze Another Resume/i });
    fireEvent.click(resetBtn);
    expect(handleReset).toHaveBeenCalledTimes(1);
  });

  it('renders CategoryBreakdown with points and explanation', () => {
    render(<CategoryBreakdown categories={mockResponse.category_scores} />);

    expect(screen.getByText('Job-Relevant Keyword Coverage')).toBeInTheDocument();
    expect(screen.getByText(/28 \/ 35 pts \(80%\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Matched 8 of 10 keywords/i)).toBeInTheDocument();

    expect(screen.getByText('Required and Preferred Skills Match')).toBeInTheDocument();
    expect(screen.getByText(/20 \/ 25 pts \(80%\)/i)).toBeInTheDocument();
  });

  it('handles empty category scores array gracefully', () => {
    const { container } = render(<CategoryBreakdown categories={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders KeywordAnalysis with matched, genuinely missing, and weakly evidenced items', () => {
    render(
      <KeywordAnalysis
        matchedRequirements={mockResponse.matched_requirements}
        missingRequirements={mockResponse.missing_requirements}
        keywordsFound={mockResponse.keywords_found}
      />
    );

    // Keywords chips
    expect(screen.getByText('python')).toBeInTheDocument();
    expect(screen.getByText('fastapi')).toBeInTheDocument();
    expect(screen.getByText('docker')).toBeInTheDocument();

    // Matched requirements
    expect(screen.getByText('Experience with Python and FastAPI')).toBeInTheDocument();

    // Genuinely missing
    expect(screen.getByText('Kubernetes container orchestration')).toBeInTheDocument();
    expect(screen.getByText(/Missing \(mandatory\)/i)).toBeInTheDocument();

    // Weakly evidenced
    expect(screen.getByText('AWS Cloud Deployment')).toBeInTheDocument();
    expect(screen.getByText(/Weak Evidence/i)).toBeInTheDocument();
  });

  it('renders RecommendationsList with priority tags', () => {
    render(<RecommendationsList recommendations={mockResponse.recommendations} />);

    expect(screen.getByText('Address Missing Core Skill: Kubernetes')).toBeInTheDocument();
    expect(screen.getByText(/high Priority/i)).toBeInTheDocument();
    expect(screen.getByText(/Highlight container orchestration tools/i)).toBeInTheDocument();
    expect(screen.getByText(/Do not engage in keyword stuffing/i)).toBeInTheDocument();
  });

  it('handles empty recommendations array gracefully', () => {
    const { container } = render(<RecommendationsList recommendations={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
