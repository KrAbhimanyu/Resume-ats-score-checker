import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AnalysisPage } from '../pages/AnalysisPage';
import * as api from '../services/analysisApi';
import { ANALYSIS_PROGRESS_TEMPLATE } from '../components/AnalysisProgressView';
import { AnalysisResponse, AnalysisSessionSnapshot } from '../types/analysis';

const mockAnalysisResult: AnalysisResponse = {
  overall_score: 91.0,
  score_label: 'Estimated Resume–Job Match Score',
  match_tier: 'Exceptional Match',
  summary: 'Exceptional match with target job description.',
  category_scores: [
    {
      category_id: 'keyword_coverage',
      category_name: 'Job-Relevant Keyword Coverage',
      score: 34.0,
      max_score: 35.0,
      percentage: 97.1,
      explanation: 'Matched 12 of 12 target keywords.',
      details: {},
    },
  ],
  matched_requirements: [
    {
      requirement: '4+ years Python',
      category: 'skill',
      matched_terms: ['python'],
      evidence_strength: 'strong',
      is_mandatory: true,
    },
  ],
  missing_requirements: [],
  keywords_found: ['python', 'fastapi'],
  recommendations: [],
  document_metadata: {
    filename: 'senior_engineer.pdf',
    file_type: '.pdf',
    file_size_bytes: 1800,
    character_count: 850,
    word_count: 130,
    extraction_warnings: [],
  },
  limitations_disclaimer: 'This score is an Estimated Resume–Job Match Score.',
};

describe('AnalysisPage Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
    vi.spyOn(api, 'createAnalysisSession').mockResolvedValue({
      session_id: 'session-1',
      created_at: '2026-11-20T00:00:00Z',
      layers: ANALYSIS_PROGRESS_TEMPLATE,
    });
    vi.spyOn(api, 'streamAnalysisProgress').mockImplementation(
      async () => {}
    );
    vi.spyOn(api, 'failAnalysisSession').mockResolvedValue({
      session_id: 'session-1',
      status: 'failed',
      created_at: '2026-11-20T00:00:00Z',
      layers: ANALYSIS_PROGRESS_TEMPLATE,
      events: [],
      report_available: false,
      error_code: 'ANALYSIS_FAILED',
    } satisfies AnalysisSessionSnapshot);
  });

  it('restores a completed report from the saved analysis session after refresh', async () => {
    window.localStorage.setItem('resume-ats-active-analysis-session', 'session-1');
    vi.spyOn(api, 'getAnalysisSession').mockResolvedValueOnce({
      session_id: 'session-1',
      status: 'completed',
      created_at: '2026-11-20T00:00:00Z',
      layers: ANALYSIS_PROGRESS_TEMPLATE,
      events: [],
      result: mockAnalysisResult,
      report_available: true,
    });

    render(<AnalysisPage />);

    expect(await screen.findByText('91')).toBeInTheDocument();
    expect(api.streamAnalysisProgress).not.toHaveBeenCalled();
  });

  it('shows validation errors when submitting with missing file and empty job description', async () => {
    render(<AnalysisPage />);

    const submitBtn = screen.getByRole('button', { name: /Analyze Resume/i });
    fireEvent.click(submitBtn);

    expect(await screen.findByText(/Please upload your resume/i)).toBeInTheDocument();
    expect(await screen.findByText(/Please paste the target job description/i)).toBeInTheDocument();
  });

  it('shows error when job description is too short (< 5 words)', async () => {
    render(<AnalysisPage />);

    // Select file
    const fileInput = screen.getByLabelText(/Upload resume file/i);
    const file = new File(['content'], 'resume.pdf', { type: 'application/pdf' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Enter short JD
    const jdTextarea = screen.getByLabelText(/Job Description/i);
    fireEvent.change(jdTextarea, { target: { value: 'Python developer' } }); // 2 words

    const submitBtn = screen.getByRole('button', { name: /Analyze Resume/i });
    fireEvent.click(submitBtn);

    expect(
      await screen.findByText(/Job description contains insufficient content \(at least 5 words required\)/i)
    ).toBeInTheDocument();
  });

  it('submits form, shows loading state, and renders results upon success', async () => {
    const analyzeSpy = vi.spyOn(api, 'analyzeResume').mockResolvedValueOnce(mockAnalysisResult);

    render(<AnalysisPage />);

    // Select file
    const fileInput = screen.getByLabelText(/Upload resume file/i);
    const file = new File(['%PDF-1.4 mock content'], 'alex_resume.pdf', { type: 'application/pdf' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Fill job description
    const jdTextarea = screen.getByLabelText(/Job Description/i);
    fireEvent.change(jdTextarea, {
      target: { value: 'Looking for a Senior Python Engineer with FastAPI and Docker experience.' },
    });

    const submitBtn = screen.getByRole('button', { name: /Analyze Resume/i });
    fireEvent.click(submitBtn);

    // Verify analyzeResume was called with correct arguments
    await waitFor(() => expect(analyzeSpy).toHaveBeenCalledTimes(1));

    // Results dashboard should appear
    await waitFor(() => {
      expect(screen.getByText('91')).toBeInTheDocument();
      expect(screen.getByText('Exceptional Match')).toBeInTheDocument();
      expect(screen.getAllByText('Job-Relevant Keyword Coverage')).toHaveLength(2);
    });
  });

  it('prevents duplicate submissions while request is in flight', async () => {
    let resolveAnalysis: (val: AnalysisResponse) => void;
    const promise = new Promise<AnalysisResponse>((resolve) => {
      resolveAnalysis = resolve;
    });

    const analyzeSpy = vi.spyOn(api, 'analyzeResume').mockReturnValueOnce(promise);

    render(<AnalysisPage />);

    // Select file
    const fileInput = screen.getByLabelText(/Upload resume file/i);
    const file = new File(['mock content'], 'alex_resume.pdf', { type: 'application/pdf' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Fill JD
    const jdTextarea = screen.getByLabelText(/Job Description/i);
    fireEvent.change(jdTextarea, {
      target: { value: 'Senior Software Engineer with Python and FastAPI experience.' },
    });

    const submitBtn = screen.getByRole('button', { name: /Analyze Resume/i });
    fireEvent.click(submitBtn);

    // Should enter loading state
    expect(await screen.findByText(/Live 5-Layer ATS Scan/i)).toBeInTheDocument();
    expect(screen.getByText(/Layer 1: Resume Parsing/i)).toBeInTheDocument();
    expect(screen.getByText(/Layer 2: Section Detection/i)).toBeInTheDocument();
    expect(screen.getByText(/Layer 3: Skills and Keyword Matching/i)).toBeInTheDocument();
    expect(screen.getByText(/Layer 4: Experience and Impact Analysis/i)).toBeInTheDocument();
    expect(screen.getByText(/Layer 5: ATS Scoring and Recommendations/i)).toBeInTheDocument();

    // Trying to click submit again while loading should not trigger another call
    fireEvent.click(submitBtn);
    await waitFor(() => expect(analyzeSpy).toHaveBeenCalledTimes(1));

    // Complete the call
    // @ts-expect-error assigned in promise
    resolveAnalysis(mockAnalysisResult);

    await waitFor(() => {
      expect(screen.getByText('91')).toBeInTheDocument();
    });
  });

  it('lets a refreshed or stalled session stop and return to the upload form', async () => {
    const analyzeSpy = vi.spyOn(api, 'analyzeResume').mockImplementationOnce(
      (_file, _job, signal) => new Promise<AnalysisResponse>((_resolve, reject) => {
        signal?.addEventListener(
          'abort',
          () => reject(new DOMException('The operation was aborted.', 'AbortError')),
          { once: true }
        );
      })
    );

    render(<AnalysisPage />);
    fireEvent.change(screen.getByLabelText(/Upload resume file/i), {
      target: { files: [new File(['mock content'], 'alex_resume.pdf', { type: 'application/pdf' })] },
    });
    fireEvent.change(screen.getByLabelText(/Job Description/i), {
      target: { value: 'Senior Software Engineer with Python and FastAPI experience.' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Analyze Resume/i }));

    await waitFor(() => expect(analyzeSpy).toHaveBeenCalledTimes(1));
    fireEvent.click(await screen.findByRole('button', { name: /Stop analysis and return to upload/i }));

    expect(await screen.findByLabelText(/Upload resume file/i)).toBeInTheDocument();
    expect(api.failAnalysisSession).toHaveBeenCalledWith('session-1');
    expect(window.localStorage.getItem('resume-ats-active-analysis-session')).toBeNull();
  });

  it('renders API error message when backend fails', async () => {
    vi.spyOn(api, 'analyzeResume').mockRejectedValueOnce(
      new api.AnalysisApiError('The resume file is corrupted or could not be parsed.', 'EXTRACTION_FAILED', 422)
    );

    render(<AnalysisPage />);

    // Select file
    const fileInput = screen.getByLabelText(/Upload resume file/i);
    const file = new File(['corrupt bytes'], 'corrupt.pdf', { type: 'application/pdf' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Fill JD
    const jdTextarea = screen.getByLabelText(/Job Description/i);
    fireEvent.change(jdTextarea, {
      target: { value: 'Senior Software Engineer with Python and FastAPI experience.' },
    });

    const submitBtn = screen.getByRole('button', { name: /Analyze Resume/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/The resume file is corrupted or could not be parsed/i)).toBeInTheDocument();
      expect(screen.getByText(/EXTRACTION_FAILED/i)).toBeInTheDocument();
    });
  });
});
