import type { ApiResponse } from '@/types'

const API_BASE =
  process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'http://10.0.2.2:8000'

// The auth store registers a getter here after hydration so every request can
// attach the current JWT without importing the store (avoids a cycle).
let tokenGetter: () => string | null = () => null

export function setTokenGetter(fn: () => string | null) {
  tokenGetter = fn
}

export function getApiBase(): string {
  return API_BASE
}

export function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...extra }
  const token = tokenGetter()
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

export class ApiClientError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: number,
    public readonly requestId?: string,
  ) {
    super(message)
    this.name = 'ApiClientError'
  }
}

async function handle<T>(res: Response): Promise<ApiResponse<T>> {
  let json: unknown
  try {
    json = await res.json()
  } catch {
    throw new ApiClientError('Invalid server response', 'BAD_RESPONSE', res.status)
  }
  if (!res.ok) {
    const err = json as { error?: { message?: string; code?: string }; request_id?: string }
    throw new ApiClientError(
      err.error?.message ?? 'Request failed',
      err.error?.code ?? 'UNKNOWN',
      res.status,
      err.request_id,
    )
  }
  return json as ApiResponse<T>
}

export const apiClient = {
  async get<T>(path: string): Promise<ApiResponse<T>> {
    const res = await fetch(`${API_BASE}${path}`, { method: 'GET', headers: authHeaders() })
    return handle<T>(res)
  },

  async post<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(body ?? {}),
    })
    return handle<T>(res)
  },

  async del<T>(path: string): Promise<ApiResponse<T>> {
    const res = await fetch(`${API_BASE}${path}`, { method: 'DELETE', headers: authHeaders() })
    return handle<T>(res)
  },
}
