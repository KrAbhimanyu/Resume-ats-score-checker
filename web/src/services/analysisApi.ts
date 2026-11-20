import {
  AnalysisResponse,
  HealthResponse,
  ApiErrorResponse,
  BulletImprovementResponse,
  AnalysisProgressEvent,
  AnalysisSessionCreated,
  AnalysisSessionSnapshot,
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

const SESSION_HEADER = 'X-Analysis-Session-Id';

async function readSessionResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new AnalysisApiError(
      `Analysis progress service returned HTTP ${response.status}.`,
      'PROGRESS_SESSION_ERROR',
      response.status
    );
  }
  return (await response.json()) as T;
}

export async function createAnalysisSession(signal?: AbortSignal): Promise<AnalysisSessionCreated> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/analyze/session`, {
    method: 'POST',
    signal,
  });
  return readSessionResponse<AnalysisSessionCreated>(response);
}

export async function getAnalysisSession(
  sessionId: string,
  signal?: AbortSignal
): Promise<AnalysisSessionSnapshot> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/analyze/session`, {
    headers: { [SESSION_HEADER]: sessionId },
    signal,
  });
  return readSessionResponse<AnalysisSessionSnapshot>(response);
}

export async function failAnalysisSession(
  sessionId: string,
  signal?: AbortSignal
): Promise<AnalysisSessionSnapshot> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/analyze/session/fail`, {
    method: 'POST',
    headers: {
      [SESSION_HEADER]: sessionId,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ error_code: 'CLIENT_INTERRUPTED' }),
    signal,
  });
  return readSessionResponse<AnalysisSessionSnapshot>(response);
}

const abortableDelay = (delayMs: number, signal: AbortSignal): Promise<void> =>
  new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException('The operation was aborted.', 'AbortError'));
      return;
    }
    const timer = window.setTimeout(() => {
      signal.removeEventListener('abort', handleAbort);
      resolve();
    }, delayMs);
    const handleAbort = () => {
      window.clearTimeout(timer);
      reject(new DOMException('The operation was aborted.', 'AbortError'));
    };
    signal.addEventListener('abort', handleAbort, { once: true });
  });

export async function streamAnalysisProgress(
  sessionId: string,
  onEvent: (event: AnalysisProgressEvent) => void,
  onSnapshot: (snapshot: AnalysisSessionSnapshot) => void,
  onConnectionChange: (connected: boolean) => void,
  signal: AbortSignal,
  afterEventId = 0
): Promise<void> {
  let lastEventId = afterEventId;
  let retryDelay = 500;
  const url = `${getApiBaseUrl()}/api/v1/analyze/session/events`;

  while (!signal.aborted) {
    try {
      const response = await fetch(`${url}?after_id=${lastEventId}`, {
        headers: {
          [SESSION_HEADER]: sessionId,
          ...(lastEventId > 0 ? { 'Last-Event-ID': String(lastEventId) } : {}),
        },
        signal,
      });
      if (!response.ok) {
        throw new AnalysisApiError(
          `Analysis progress stream returned HTTP ${response.status}.`,
          'PROGRESS_STREAM_ERROR',
          response.status
        );
      }
      if (!response.body) {
        throw new AnalysisApiError(
          'The analysis progress stream is unavailable in this browser.',
          'PROGRESS_STREAM_UNAVAILABLE',
          0
        );
      }

      onConnectionChange(true);
      retryDelay = 500;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      try {
        while (!signal.aborted) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
          const messages = buffer.split('\n\n');
          buffer = messages.pop() ?? '';
          for (const message of messages) {
            let eventId: number | undefined;
            let eventName = 'message';
            const dataLines: string[] = [];
            for (const line of message.split('\n')) {
              if (line.startsWith('id:')) eventId = Number(line.slice(3).trim());
              else if (line.startsWith('event:')) eventName = line.slice(6).trim();
              else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
            }
            if (eventName !== 'progress' || dataLines.length === 0) continue;
            let event: AnalysisProgressEvent;
            try {
              event = JSON.parse(dataLines.join('\n')) as AnalysisProgressEvent;
            } catch {
              throw new AnalysisApiError(
                'The server sent an unreadable analysis progress event.',
                'INVALID_PROGRESS_EVENT',
                500
              );
            }
            if (!Number.isInteger(event.event_id) || event.event_id <= lastEventId) continue;
            lastEventId = Math.max(event.event_id, eventId ?? 0);
            onEvent(event);
          }
        }
      } finally {
        reader.releaseLock();
      }

      if (signal.aborted) return;
      onConnectionChange(false);
      const snapshot = await getAnalysisSession(sessionId, signal);
      onSnapshot(snapshot);
      if (snapshot.status === 'completed' || snapshot.status === 'failed') return;
    } catch (error: unknown) {
      if (signal.aborted || (error instanceof DOMException && error.name === 'AbortError')) return;
      if (
        error instanceof AnalysisApiError
        && ['INVALID_PROGRESS_EVENT', 'PROGRESS_STREAM_UNAVAILABLE'].includes(error.code)
      ) {
        onConnectionChange(false);
        throw error;
      }
      if (error instanceof AnalysisApiError && error.statusCode >= 400 && error.statusCode < 500) {
        onConnectionChange(false);
        throw error;
      }
      onConnectionChange(false);
      try {
        const snapshot = await getAnalysisSession(sessionId, signal);
        onSnapshot(snapshot);
        if (snapshot.status === 'completed' || snapshot.status === 'failed') return;
      } catch (snapshotError: unknown) {
        if (signal.aborted || (snapshotError instanceof DOMException && snapshotError.name === 'AbortError')) {
          return;
        }
        if (
          snapshotError instanceof AnalysisApiError
          && snapshotError.statusCode >= 400
          && snapshotError.statusCode < 500
        ) {
          throw snapshotError;
        }
      }
      await abortableDelay(retryDelay, signal);
      retryDelay = Math.min(5000, retryDelay * 2);
    }
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
  signal?: AbortSignal,
  analysisSessionId?: string
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
      headers: analysisSessionId ? { [SESSION_HEADER]: analysisSessionId } : undefined,
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
  signal?: AbortSignal,
  options?: {
    templateId?: string;
    internationalFormat?: string;
    fontFamily?: string;
    sectionOrder?: string[];
    hiddenSections?: string[];
  }
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
        template_id: options?.templateId || 'ats-essential-navy',
        international_format: options?.internationalFormat || 'us',
        font_family: options?.fontFamily || 'Calibri',
        section_order: options?.sectionOrder,
        hidden_sections: options?.hiddenSections,
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
