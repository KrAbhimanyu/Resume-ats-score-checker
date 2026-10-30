import {
  AnalysisResponse,
  HealthResponse,
  ApiErrorResponse,
  BulletImprovementResponse,
} from '../types/analysis';
import { TargetedAnalysisResponse, StructuredResume } from '../types/builder';

/**
 * Resolves the API base URL.
 * Defaults to empty string in development with Vite proxy or http://127.0.0.1:8000.
 */
export const getApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl !== undefined && envUrl !== '') {
    // Strip trailing slash if present
    return envUrl.endsWith('/') ? envUrl.slice(0, -1) : envUrl;
  }
  // If no env is set, use empty string to rely on Vite proxy / local host
  return 'http://127.0.0.1:8000';
};

export class AnalysisApiError extends Error {
  code: string;
  statusCode: number;
  details?: Record<string, unknown>;

  constructor(message: string, code = 'ANALYSIS_ERROR', statusCode = 400, details?: Record<string, unknown>) {
    super(message);
    this.name = 'AnalysisApiError';
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * Health check endpoint service.
 */
export async function checkHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/health`;

  try {
    const res = await fetch(url, { signal });
    if (!res.ok) {
      throw new AnalysisApiError(
        `Backend service returned HTTP ${res.status}`,
        'HEALTH_CHECK_FAILED',
        res.status
      );
    }
    return (await res.json()) as HealthResponse;
  } catch (err: unknown) {
    if (err instanceof AnalysisApiError) throw err;
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw err;
    }
    const message = err instanceof Error ? err.message : 'Unable to connect to the backend service.';
    throw new AnalysisApiError(
      `Health check failed: ${message}. Make sure the backend server is running on http://127.0.0.1:8000.`,
      'NETWORK_ERROR',
      0
    );
  }
}

/**
 * Sends resume file and job description to POST /api/v1/analyze
 */
export async function analyzeResume(
  resumeFile: File,
  jobDescription: string,
  signal?: AbortSignal
): Promise<AnalysisResponse> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/analyze`;

  // Basic client-side guard
  if (!resumeFile) {
    throw new AnalysisApiError('Please select a resume file (.pdf or .docx).', 'MISSING_FILE', 400);
  }
  if (!jobDescription || !jobDescription.trim()) {
    throw new AnalysisApiError('Please enter a job description.', 'EMPTY_JOB_DESCRIPTION', 400);
  }

  // Build multipart form data matching backend endpoint parameters:
  // resume_file: UploadFile
  // job_description: str
  const formData = new FormData();
  formData.append('resume_file', resumeFile, resumeFile.name);
  formData.append('job_description', jobDescription.trim());

  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      body: formData,
      signal,
    });
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw err;
    }
    const msg = err instanceof Error ? err.message : 'Network connection failure';
    throw new AnalysisApiError(
      `Could not connect to analysis service (${msg}). Ensure the backend is active at ${baseUrl}.`,
      'NETWORK_FAILURE',
      0
    );
  }

  // Handle errors
  if (!response.ok) {
    let errorData: ApiErrorResponse | null = null;
    try {
      errorData = (await response.json()) as ApiErrorResponse;
    } catch {
      // Non-JSON response
    }

    if (errorData?.error) {
      throw new AnalysisApiError(
        errorData.error.message || 'An error occurred during resume analysis.',
        errorData.error.code || 'API_ERROR',
        response.status,
        errorData.error.details
      );
    }

    if (errorData?.detail && Array.isArray(errorData.detail)) {
      const messages = errorData.detail.map((d) => `${d.loc.join('.')}: ${d.msg}`).join(', ');
      throw new AnalysisApiError(
        `Validation error: ${messages}`,
        'VALIDATION_ERROR',
        response.status
      );
    }

    // Status code fallbacks
    if (response.status === 413) {
      throw new AnalysisApiError(
        'The uploaded file exceeds the 5 MB size limit. Please upload a smaller document.',
        'FILE_TOO_LARGE',
        413
      );
    }
    if (response.status === 422) {
      throw new AnalysisApiError(
        'The resume file could not be read or does not contain readable text.',
        'UNPROCESSABLE_DOCUMENT',
        422
      );
    }

    throw new AnalysisApiError(
      `Analysis failed with status ${response.status}. Please try again.`,
      'SERVER_ERROR',
      response.status
    );
  }

  try {
    const data = (await response.json()) as AnalysisResponse;

    // Validate expected structure
    if (typeof data.overall_score !== 'number' || !Array.isArray(data.category_scores)) {
      throw new Error('Response payload does not match expected analysis schema.');
    }

    return data;
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Invalid JSON';
    throw new AnalysisApiError(
      `Failed to parse server response: ${msg}`,
      'INVALID_RESPONSE',
      500
    );
  }
}

/**
 * Sends a single bullet point to POST /api/v1/improve-bullet for on-the-fly rewriting.
 */
export async function improveBullet(
  bulletText: string,
  targetSkills?: string[],
  signal?: AbortSignal
): Promise<BulletImprovementResponse> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/improve-bullet`;

  if (!bulletText || !bulletText.trim()) {
    throw new AnalysisApiError('Please enter a bullet point to analyze.', 'EMPTY_BULLET', 400);
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        bullet_text: bulletText.trim(),
        target_skills: targetSkills,
      }),
      signal,
    });
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw err;
    }
    const msg = err instanceof Error ? err.message : 'Network error';
    throw new AnalysisApiError(
      `Could not connect to bullet improvement service (${msg}).`,
      'NETWORK_FAILURE',
      0
    );
  }

  if (!response.ok) {
    throw new AnalysisApiError(
      `Bullet improvement request failed with HTTP ${response.status}`,
      'API_ERROR',
      response.status
    );
  }

  return (await response.json()) as BulletImprovementResponse;
}

/**
 * Analyzes resume against target company and role for Targeted Resume Builder.
 */
export async function analyzeAndPlanTargetedResume(
  params: {
    resumeFile?: File | null;
    resumeText?: string;
    targetMode: string;
    companyName: string;
    industry?: string;
    jobTitle: string;
    jobDescription?: string;
    sectionsToImprove?: string[];
  },
  signal?: AbortSignal
): Promise<TargetedAnalysisResponse> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/builder/analyze-and-plan`;

  const formData = new FormData();
  if (params.resumeFile) {
    formData.append('resume_file', params.resumeFile, params.resumeFile.name);
  }
  if (params.resumeText) {
    formData.append('resume_text', params.resumeText);
  }
  formData.append('target_mode', params.targetMode);
  formData.append('company_name', params.companyName);
  formData.append('job_title', params.jobTitle);
  if (params.industry) {
    formData.append('industry', params.industry);
  }
  if (params.jobDescription) {
    formData.append('job_description', params.jobDescription);
  }
  if (params.sectionsToImprove && params.sectionsToImprove.length > 0) {
    formData.append('sections_to_improve', params.sectionsToImprove.join(','));
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      body: formData,
      signal,
    });
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err;
    const msg = err instanceof Error ? err.message : 'Network failure';
    throw new AnalysisApiError(`Could not connect to target builder service (${msg}).`, 'NETWORK_FAILURE', 0);
  }

  if (!response.ok) {
    let errorMsg = `Targeted analysis failed with HTTP ${response.status}`;
    try {
      const errData = await response.json();
      if (errData?.detail) errorMsg = errData.detail;
      else if (errData?.error?.message) errorMsg = errData.error.message;
    } catch {
      // ignore
    }
    throw new AnalysisApiError(errorMsg, 'BUILDER_ERROR', response.status);
  }

  return (await response.json()) as TargetedAnalysisResponse;
}

/**
 * Exports approved structured resume as a downloadable binary Blob (PDF or DOCX).
 */
export async function exportResume(
  resume: StructuredResume,
  format: 'pdf' | 'docx',
  filename?: string,
  signal?: AbortSignal
): Promise<Blob> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/builder/export`;

  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        format,
        resume,
        filename: filename || 'targeted_resume',
      }),
      signal,
    });
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err;
    const msg = err instanceof Error ? err.message : 'Network failure';
    throw new AnalysisApiError(`Could not export resume (${msg}).`, 'NETWORK_FAILURE', 0);
  }

  if (!response.ok) {
    throw new AnalysisApiError(`Resume export failed with HTTP ${response.status}`, 'EXPORT_ERROR', response.status);
  }

  return await response.blob();
}

