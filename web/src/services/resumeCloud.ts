import { getApiBaseUrl } from './analysisApi';
import { ResumeCloudDocument } from '../types/builder';

export const RESUME_SESSION_TOKEN_KEY = 'career-platform-token';

export const getResumeSessionToken = (): string =>
  window.sessionStorage.getItem(RESUME_SESSION_TOKEN_KEY) || '';

const request = async <T>(
  token: string,
  path: string,
  options: RequestInit = {},
): Promise<T> => {
  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${token}`);
  if (options.body) headers.set('Content-Type', 'application/json');
  const response = await fetch(`${getApiBaseUrl()}/api/v1/builder${path}`, {
    ...options,
    headers,
  });
  if (!response.ok) {
    let message = `Resume cloud storage failed with HTTP ${response.status}.`;
    try {
      const payload = await response.json() as { detail?: string };
      message = payload.detail || message;
    } catch {
      // The response may not contain JSON.
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return await response.json() as T;
};

export const loadCloudResumeDocuments = <T>(
  token: string,
  type: 'profile' | 'version',
): Promise<ResumeCloudDocument<T>[]> =>
  request(token, `/resumes?document_type=${type}`);

export const saveCloudResumeDocument = <T>(
  token: string,
  document: { id: string; document_type: 'profile' | 'version'; name: string; document: T },
): Promise<ResumeCloudDocument<T>> =>
  request(token, `/resumes/${encodeURIComponent(document.id)}`, {
    method: 'PUT',
    body: JSON.stringify(document),
  });

export const deleteCloudResumeDocument = (
  token: string,
  id: string,
): Promise<void> =>
  request(token, `/resumes/${encodeURIComponent(id)}`, { method: 'DELETE' });
