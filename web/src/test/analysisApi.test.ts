import { describe, it, expect, vi, beforeEach } from 'vitest';
import { analyzeResume, checkHealth, improveBullet, AnalysisApiError } from '../services/analysisApi';
import { AnalysisResponse } from '../types/analysis';

const mockSuccessResponse: AnalysisResponse = {
  overall_score: 84.5,
  score_label: 'Estimated Resume–Job Match Score',
  match_tier: 'Strong Match',
  summary: 'Your resume achieved an Estimated Resume–Job Match Score of 84.5/100.',
  category_scores: [
    {
      category_id: 'keyword_coverage',
      category_name: 'Job-Relevant Keyword Coverage',
      score: 30.0,
      max_score: 35.0,
      percentage: 85.7,
      explanation: 'Matched 6 of 7 keywords.',
      details: {},
    },
  ],
  matched_requirements: [
    {
      requirement: 'Python and FastAPI',
      category: 'skill',
      matched_terms: ['python', 'fastapi'],
      evidence_strength: 'strong',
      is_mandatory: true,
    },
  ],
  missing_requirements: [
    {
      requirement: 'Kubernetes',
      category: 'skill',
      importance: 'preferred',
      reason: 'Not found in resume.',
      is_evidenced_elsewhere: false,
    },
  ],
  keywords_found: ['python', 'fastapi', 'docker'],
  recommendations: [
    {
      id: 'rec-1',
      category: 'skills',
      title: 'Address Missing Skill: Kubernetes',
      description: 'Highlight any transferable container orchestration experience.',
      action_type: 'add_missing_keyword',
      priority: 'medium',
    },
  ],
  document_metadata: {
    filename: 'test_resume.pdf',
    file_type: '.pdf',
    file_size_bytes: 2048,
    character_count: 500,
    word_count: 85,
    extraction_warnings: [],
  },
  limitations_disclaimer: 'This score is an Estimated Resume–Job Match Score calculated via deterministic heuristic analysis.',
};

describe('analysisApi Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('checkHealth', () => {
    it('returns HealthResponse when backend is healthy', async () => {
      const mockHealth = {
        status: 'healthy',
        version: '1.0.0',
        timestamp: '2026-10-19T18:00:00Z',
        service: 'Resume ATS Score Checker API',
      };

      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(mockHealth), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );

      const res = await checkHealth();
      expect(res.status).toBe('healthy');
      expect(res.version).toBe('1.0.0');
    });

    it('throws AnalysisApiError when fetch fails', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Connection refused'));

      await expect(checkHealth()).rejects.toThrow(AnalysisApiError);
    });
  });

  describe('analyzeResume', () => {
    it('successfully uploads file and returns AnalysisResponse', async () => {
      let capturedFormData: FormData | null = null;

      vi.spyOn(globalThis, 'fetch').mockImplementationOnce(async (_url, init) => {
        capturedFormData = init?.body as FormData;
        return new Response(JSON.stringify(mockSuccessResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      });

      const file = new File(['%PDF-1.4 mock content'], 'alex_resume.pdf', { type: 'application/pdf' });
      const jd = 'Looking for Python and FastAPI engineer.';

      const result = await analyzeResume(file, jd);

      expect(result.overall_score).toBe(84.5);
      expect(result.match_tier).toBe('Strong Match');
      expect(capturedFormData).not.toBeNull();
      const fd = capturedFormData as unknown as FormData;
      expect(fd.get('resume_file')).toBeDefined();
      expect(fd.get('job_description')).toBe(jd);
    });

    it('rejects client-side if file is missing', async () => {
      // @ts-expect-error testing null input
      await expect(analyzeResume(null, 'Some JD')).rejects.toThrow('Please select a resume file');
    });

    it('rejects client-side if job description is empty', async () => {
      const file = new File(['content'], 'resume.pdf');
      await expect(analyzeResume(file, '   ')).rejects.toThrow('Please enter a job description');
    });

    it('handles backend domain error with structured error envelope', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            error: {
              code: 'EMPTY_RESUME',
              message: 'The uploaded resume contains insufficient readable text.',
            },
          }),
          { status: 422, headers: { 'Content-Type': 'application/json' } }
        )
      );

      const file = new File(['mock content'], 'empty.pdf');
      await expect(analyzeResume(file, 'Some valid job description')).rejects.toThrow(
        'The uploaded resume contains insufficient readable text.'
      );
    });

    it('handles 413 file size exceeded response', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('', { status: 413 })
      );

      const file = new File(['mock content'], 'large.pdf');
      await expect(analyzeResume(file, 'Job description')).rejects.toThrow(
        'The uploaded file exceeds the 5 MB size limit.'
      );
    });

    it('handles network failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Network error'));

      const file = new File(['mock content'], 'resume.pdf');
      await expect(analyzeResume(file, 'Job description')).rejects.toThrow(
        'Could not connect to analysis service'
      );
    });
  });

  describe('improveBullet', () => {
    it('successfully sends bullet and returns BulletImprovementResponse', async () => {
      const mockBulletResponse = {
        original_text: 'Worked on API testing.',
        is_weak: true,
        issues: ["Starts with passive phrasing 'Worked on'"],
        suggested_rewrite: 'Tested REST APIs using Postman, achieving [add verified result].',
        what_to_add: 'Add tools and metrics.',
        recommended_action_verbs: ['Tested', 'Validated'],
      };

      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(mockBulletResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );

      const res = await improveBullet('Worked on API testing.', ['Postman']);
      expect(res.is_weak).toBe(true);
      expect(res.suggested_rewrite).toContain('Tested REST APIs');
      expect(res.recommended_action_verbs).toContain('Tested');
    });

    it('rejects client-side if bullet text is empty', async () => {
      await expect(improveBullet('')).rejects.toThrow('Please enter a bullet point to analyze.');
      await expect(improveBullet('   ')).rejects.toThrow('Please enter a bullet point to analyze.');
    });

    it('handles HTTP error responses from server', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('', { status: 500 })
      );

      await expect(improveBullet('Some bullet text')).rejects.toThrow(
        'Bullet improvement request failed with HTTP 500'
      );
    });
  });
});

