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
  subject: string | null
  chapter: string | null
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
  subject?: string
  chapter?: string
}

export interface SubjectCountDto {
  subject: string
  count: number
}

export interface ConversationWithMessagesDto {
  conversation: ConversationDto
  messages: MessageDto[]
}

// ── Streaming DTOs ───────────────────────────────────────────────────────────

export interface StreamSourceDto {
  title: string | null
  score: number
  subject: string | null
  chapter: string | null
}

export interface StreamMetaDto {
  type: 'meta'
  conversation_id: UUID
  subject: string | null
  chapter: string | null
  rag: {
    has_context: boolean
    source_count: number
    cascade_level: string
    sources: StreamSourceDto[]
  }
}

export interface StreamChunkDto {
  type: 'chunk' | 'done' | 'error'
  content?: string
  conversation_id?: UUID
  message_id?: UUID
  error?: string
}
