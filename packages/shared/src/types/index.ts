export type UUID = string

export type Role = 'user' | 'assistant' | 'system'

export type Theme = 'light' | 'dark' | 'system'

export type AppEnv = 'development' | 'staging' | 'production'

export interface Timestamps {
  created_at: string
  updated_at: string
}

export interface PaginationParams {
  page: number
  limit: number
}

export interface PaginationMeta {
  page: number
  limit: number
  total: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export interface ApiResponse<T = unknown> {
  success: boolean
  data: T
  message: string
  request_id: string
}

export interface ApiError {
  success: false
  error: {
    code: string
    message: string
    details?: Record<string, unknown>
  }
  request_id: string
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  meta: PaginationMeta
}
