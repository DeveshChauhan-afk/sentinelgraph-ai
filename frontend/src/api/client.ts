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

/**
 * Base API URL derived from environment.
 * If VITE_API_URL is configured (e.g. https://api.sentinelgraph.example.com),
 * all requests are routed to that host.
 * Otherwise, defaults to relative URLs for same-origin or development proxy environments.
 */
const RAW_API_BASE_URL = import.meta.env.VITE_API_URL;
export const API_BASE_URL =
  typeof RAW_API_BASE_URL === 'string' && RAW_API_BASE_URL.trim()
    ? RAW_API_BASE_URL.trim().replace(/\/+$/, '')
    : '';

/**
 * Resolves an API path to either an absolute URL or normalized relative path.
 */
export function resolveApiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return API_BASE_URL ? `${API_BASE_URL}${normalizedPath}` : normalizedPath;
}

/**
 * Default request timeout in milliseconds (60 seconds).
 * Accommodates free-tier managed cloud cold starts (e.g. Render Free wake-from-sleep).
 */
export const DEFAULT_REQUEST_TIMEOUT_MS = 60000;

export interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

export async function apiFetch<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const url = resolveApiUrl(endpoint);
  const { timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS, ...fetchOptions } = options;

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
