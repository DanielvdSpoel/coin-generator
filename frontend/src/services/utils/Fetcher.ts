/**
 * The only place in the frontend that calls `fetch()`.
 *
 * Throws the `Response` on non-2xx so callers can inspect the status. Service
 * modules build on this; components and stores never call it directly.
 */

export const API_BASE_URL = (import.meta.env.VITE_API_URL ?? '/api').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(
    public readonly response: Response,
    public readonly body: unknown,
  ) {
    super(`API request failed with status ${response.status}`)
    this.name = 'ApiError'
  }
}

export interface FetcherOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
}

async function request(path: string, options: FetcherOptions = {}): Promise<Response> {
  const { body, headers, ...rest } = options
  const init: RequestInit = { credentials: 'same-origin', ...rest, headers: { ...headers } }

  if (body !== undefined) {
    if (body instanceof FormData) {
      init.body = body
    } else {
      init.body = JSON.stringify(body)
      init.headers = { 'Content-Type': 'application/json', ...init.headers }
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, init)
  if (!response.ok) {
    const parsed = await response
      .clone()
      .json()
      .catch(() => undefined)
    throw new ApiError(response, parsed)
  }
  return response
}

export async function jsonFetcher<T>(path: string, options?: FetcherOptions): Promise<T> {
  const response = await request(path, options)
  return (await response.json()) as T
}

export async function blobFetcher(path: string, options?: FetcherOptions): Promise<Blob> {
  const response = await request(path, options)
  return response.blob()
}
