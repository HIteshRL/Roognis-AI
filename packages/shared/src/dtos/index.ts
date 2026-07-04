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
  role?: string
  is_admin?: boolean
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

export interface AttachmentDto {
  id: UUID
  kind: string
  content_type: string
  file_size: number
  url: string
  created_at: string
}

export interface MessageDto {
  id: UUID
  conversation_id: UUID
  role: Role
  content: string
  token_count: number | null
  created_at: string
  attachments?: AttachmentDto[]
}

export interface SendMessageDto {
  message: string
  conversation_id?: UUID
  subject?: string
  chapter?: string
  attachment_ids?: UUID[]
}

export interface SubjectCountDto {
  subject: string
  count: number
}

export interface ChapterDto {
  chapter: string
  conversation_count: number
}

export interface MediaJobDto {
  id: UUID
  message_id: UUID
  conversation_id: UUID | null
  kind: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  progress: number
  attachment_id: UUID | null
  url: string | null
  error_message: string | null
  created_at: string
  updated_at: string
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

// ── Quiz DTOs ─────────────────────────────────────────────────────────────

export interface GenerateQuizDto {
  subject?: string | null
  chapter?: string | null
  concept_ids?: string[] | null
  question_count?: number
  difficulty?: string
}

export interface QuizSummaryDto {
  id: UUID
  title: string
  subject: string | null
  chapter: string | null
  difficulty: string
  question_count: number
  total_attempts: number
  best_score: number
  created_at: string
}

export interface QuizQuestionDto {
  id: UUID
  concept_name: string
  question_text: string
  question_type: string
  options: string[]
  bloom_level: string
  difficulty: string
  position: number
}

export interface QuizDetailDto {
  id: UUID
  title: string
  subject: string | null
  chapter: string | null
  difficulty: string
  question_count: number
  questions: QuizQuestionDto[]
  created_at: string
}

export interface SubmitResponseDto {
  question_id: string
  selected_answer: string
  time_spent_ms: number
}

export interface SubmitQuizDto {
  responses: SubmitResponseDto[]
}

export interface QuizAttemptDto {
  id: UUID
  quiz_id: UUID
  score: number
  correct_count: number
  total_answered: number
  total_time_ms: number
  started_at: string
  completed_at: string | null
}

export interface QuestionResultDto {
  question_id: UUID
  question_text: string
  options: string[]
  selected_answer: string
  correct_answer: string
  is_correct: boolean
  explanation: string
  concept_name: string
}

export interface QuizResultDto {
  attempt: QuizAttemptDto
  quiz_title: string
  quiz_subject: string | null
  results: QuestionResultDto[]
}

export interface QuizHistoryItemDto {
  attempt: QuizAttemptDto
  quiz_title: string
  quiz_subject: string | null
}
