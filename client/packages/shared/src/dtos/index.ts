import type { UUID, Role, Theme, Timestamps } from '../types'

// ── Auth DTOs ────────────────────────────────────────────────────────────────

export interface RegisterDto {
  email: string
  username: string
  password: string
}

export interface LoginDto {
  email: string
  password: string
}

export interface AuthResponseDto {
  token: string
  user: UserDto
}

// ── User DTOs ────────────────────────────────────────────────────────────────

export interface UserDto extends Timestamps {
  id: UUID
  email: string
  username: string
  is_active: boolean
  is_verified: boolean
}

export interface ProfileDto extends Timestamps {
  id: UUID
  user_id: UUID
  full_name: string | null
  avatar_url: string | null
  bio: string | null
  timezone: string
  language: string
}

export interface UpdateProfileDto {
  full_name?: string
  bio?: string
  timezone?: string
  language?: string
}

export interface SettingsDto extends Timestamps {
  id: UUID
  user_id: UUID
  theme: Theme
  notifications_enabled: boolean
  llm_model: string
  temperature: number
}

export interface UpdateSettingsDto {
  theme?: Theme
  notifications_enabled?: boolean
  llm_model?: string
  temperature?: number
}

// ── Chat DTOs ────────────────────────────────────────────────────────────────

export interface ConversationDto extends Timestamps {
  id: UUID
  user_id: UUID
  title: string | null
  is_archived: boolean
  message_count?: number
}

export interface MessageDto {
  id: UUID
  conversation_id: UUID
  role: Role
  content: string
  token_count: number | null
  created_at: string
}

export interface SendMessageDto {
  message: string
  conversation_id?: UUID
}

export interface ConversationWithMessagesDto {
  conversation: ConversationDto
  messages: MessageDto[]
}

// ── Streaming DTOs ───────────────────────────────────────────────────────────

export interface StreamChunkDto {
  type: 'chunk' | 'done' | 'error'
  content?: string
  conversation_id?: UUID
  message_id?: UUID
  error?: string
}
