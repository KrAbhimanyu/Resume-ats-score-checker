import { getApiBaseUrl } from './analysisApi';

export class CareerApiError extends Error {
  statusCode: number;

  constructor(message: string, statusCode: number) {
    super(message);
    this.name = 'CareerApiError';
    this.statusCode = statusCode;
  }
}

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown;
};

const careerUrl = (path: string): string =>
  `${getApiBaseUrl()}/api/v1/career${path.startsWith('/') ? path : `/${path}`}`;

export async function careerRequest<T>(
  token: string,
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (token && token.trim()) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let body: BodyInit | undefined;
  if (options.body instanceof FormData) {
    body = options.body;
  } else if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json');
    body = JSON.stringify(options.body);
  }

  try {
    const response = await fetch(careerUrl(path), {
      ...options,
      headers,
      body,
    });
    if (!response.ok) {
      let message = `Request failed with status ${response.status}.`;
      try {
        const payload = (await response.json()) as {
          detail?: string | { message?: string };
          error?: { message?: string };
        };
        message = (typeof payload.detail === 'string' ? payload.detail : payload.detail?.message)
          || payload.error?.message
          || message;
      } catch {
        // The response body may not contain JSON.
      }
      throw new CareerApiError(message, response.status);
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof CareerApiError) throw error;
    const networkMessage = error instanceof Error ? error.message : 'Unknown network error';
    throw new CareerApiError(
      `Unable to reach the career backend. Check that the FastAPI server is running and VITE_API_BASE_URL is configured correctly. Original error: ${networkMessage}`,
      0,
    );
  }
}

export async function exportCareerResume(
  token: string,
  resume: unknown,
  format: 'pdf' | 'docx',
): Promise<Blob> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/builder/export`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      format,
      filename: 'tailored-resume',
      resume,
      template_id: 'ats-essential-navy',
      international_format: 'us',
    }),
  });
  if (!response.ok) {
    let message = `Resume export failed with status ${response.status}.`;
    try {
      const payload = (await response.json()) as { detail?: string };
      message = payload.detail || message;
    } catch {
      // The response body may not contain JSON.
    }
    throw new CareerApiError(message, response.status);
  }
  return response.blob();
}
