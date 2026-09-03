/**
 * Centralized HTTP client for SentinelGraph API.
 * Uses native fetch with standard error classification and timeout support.
 */

export class ApiError extends Error {
  public status: number;
  public data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

export async function apiFetch<T>(url: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = 30000, ...fetchOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const headers = new Headers(fetchOptions.headers || {});
    if (!headers.has('Content-Type') && !(fetchOptions.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }
    headers.set('Accept', 'application/json');

    const response = await fetch(url, {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    });

    if (!response.ok) {
      let errorBody: any;
      try {
        errorBody = await response.json();
      } catch {
        errorBody = await response.text();
      }

      const message =
        typeof errorBody === 'object' && errorBody?.detail
          ? errorBody.detail
          : `HTTP ${response.status}: ${response.statusText}`;

      throw new ApiError(message, response.status, errorBody);
    }

    if (response.status === 204) {
      return null as T;
    }

    return (await response.json()) as T;
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw new ApiError('Request timed out while contacting intelligence server.', 408);
    }
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(err.message || 'Network connection failed.', 0);
  } finally {
    clearTimeout(timeoutId);
  }
}
