import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CareerPlatformPage } from '../pages/CareerPlatformPage';

const response = (body: unknown, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => body,
  blob: async () => new Blob(),
}) as Response;

describe('CareerPlatformPage', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it('creates a session and opens the account-scoped career workspace', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/auth/register')) {
        return response({
          access_token: 'session-token',
          user: { email: 'candidate@example.com' },
        }, 201);
      }
      if (url.endsWith('/auth/me')) {
        return response({ email: 'candidate@example.com' });
      }
      if (url.endsWith('/analytics')) {
        return response({
          job_search: {
            jobs_discovered: 0,
            jobs_saved: 0,
            jobs_applied: 0,
            average_compatibility_score: null,
          },
          application_success: {},
        });
      }
      return response({ detail: 'Unexpected test request' }, 404);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<CareerPlatformPage />);
    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: 'candidate@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'secure-password-123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Create account/i }));

    await screen.findByRole('heading', { name: 'Overview' });
    expect(await screen.findByRole('heading', { name: 'One view of your career progress.' })).toBeInTheDocument();
    await waitFor(() => {
      expect(sessionStorage.getItem('career-platform-token')).toBe('session-token');
    });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/career/auth/register'),
      expect.objectContaining({ method: 'POST' }),
    );
  });
});
