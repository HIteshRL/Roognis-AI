import type { ApiError, ApiResponse } from '@roognis/shared'
import { useAuthStore } from '@/lib/stores/auth.store'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

class ApiClient {
  private baseUrl: string
  private tokenFn: (() => Promise<string | null>) | null = null

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  setTokenProvider(fn: () => Promise<string | null>) {
    this.tokenFn = fn
  }

  private async getHeaders(): Promise<HeadersInit> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    if (this.tokenFn) {
      const token = await this.tokenFn()
      if (token) headers['Authorization'] = `Bearer ${token}`
    }
    return headers
  }

  async get<T>(path: string): Promise<ApiResponse<T>> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'GET',
      headers: await this.getHeaders(),
    })
    return this.handle<T>(res)
  }

  async post<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(body),
    })
    return this.handle<T>(res)
  }

  async put<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'PUT',
      headers: await this.getHeaders(),
      body: JSON.stringify(body),
    })
    return this.handle<T>(res)
  }

  async patch<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'PATCH',
      headers: await this.getHeaders(),
      body: JSON.stringify(body),
    })
    return this.handle<T>(res)
  }

  async delete<T>(path: string): Promise<ApiResponse<T>> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'DELETE',
      headers: await this.getHeaders(),
    })
    return this.handle<T>(res)
  }

  async upload<T>(path: string, formData: FormData): Promise<ApiResponse<T>> {
    const headers: Record<string, string> = {}
    if (this.tokenFn) {
      const token = await this.tokenFn()
      if (token) headers['Authorization'] = `Bearer ${token}`
    }
    // Note: do NOT set Content-Type — the browser sets the multipart boundary.
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers,
      body: formData,
    })
    return this.handle<T>(res)
  }

  async fetchBlobUrl(path: string): Promise<string> {
    const headers: Record<string, string> = {}
    if (this.tokenFn) {
      const token = await this.tokenFn()
      if (token) headers['Authorization'] = `Bearer ${token}`
    }
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'GET',
      headers,
    })
    if (!res.ok) {
      throw new Error(`Failed to load resource: ${res.status}`)
    }
    const blob = await res.blob()
    return URL.createObjectURL(blob)
  }

  async streamPost(path: string, body: unknown): Promise<ReadableStream<string>> {
    const headers = await this.getHeaders()
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { ...headers, Accept: 'text/event-stream' },
      body: JSON.stringify(body),
    })
    if (!res.ok || !res.body) {
      throw new Error(`Stream request failed: ${res.status}`)
    }
    return res.body.pipeThrough(new TextDecoderStream())
  }

  private async handle<T>(res: Response): Promise<ApiResponse<T>> {
    const json = await res.json()
    if (!res.ok) {
      const error = json as ApiError
      throw new ApiClientError(
        error.error?.message ?? 'Request failed',
        error.error?.code ?? 'UNKNOWN',
        res.status,
        error.request_id
      )
    }
    return json as ApiResponse<T>
  }
}

export class ApiClientError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: number,
    public readonly requestId?: string
  ) {
    super(message)
    this.name = 'ApiClientError'
  }
}

export const apiClient = new ApiClient(API_BASE)

// Attach the custom-JWT from the persisted auth store to every request.
// (Previously never wired up — requests went out unauthenticated.)
apiClient.setTokenProvider(async () => useAuthStore.getState().token)
