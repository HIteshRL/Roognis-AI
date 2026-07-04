// Vendored subset of @roognis/shared + web student types, kept self-contained so
// apps/native installs independently of the workspace. Swap for @roognis/shared
// later if apps/native is added to the root workspace.

export interface ApiResponse<T> {
  success?: boolean
  data: T
  message?: string
  request_id?: string
}

export interface Pagination {
  total: number
  page: number
  limit: number
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: Pagination
}

// ── Auth / user ───────────────────────────────────────────────────────────────

export interface UserDto {
  id: string
  email: string
  username: string
  is_active: boolean
  is_verified: boolean
  created_at: string
  updated_at: string
}

export interface AuthResponseDto {
  token: string
  user: UserDto
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export type Role = 'user' | 'assistant' | 'system'

export interface AttachmentDto {
  id: string
  kind: string
  content_type: string
  file_size: number
  url: string
  created_at: string
}

export interface MessageDto {
  id: string
  conversation_id: string
  role: Role
  content: string
  token_count: number | null
  created_at: string
  attachments?: AttachmentDto[]
}

export interface ConversationDto {
  id: string
  user_id: string
  title: string | null
  subject: string | null
  chapter: string | null
  is_archived: boolean
  message_count?: number
  created_at: string
  updated_at: string
}

export interface ConversationWithMessagesDto {
  conversation: ConversationDto
  messages: MessageDto[]
}

export interface SubjectCountDto {
  subject: string
  count: number
}

export interface ChapterDto {
  chapter: string
  conversation_count: number
}

export interface StreamSourceDto {
  title: string | null
  score: number
  subject?: string | null
  chapter?: string | null
}

// A single parsed SSE event from POST /api/v1/chat.
export interface ChatStreamEvent {
  type: 'meta' | 'chunk' | 'image' | 'done' | string
  content?: string
  conversation_id?: string
  attachment_id?: string
  rag?: {
    has_context: boolean
    source_count: number
    cascade_level?: string
    sources?: StreamSourceDto[]
  }
}

// ── Student ─────────────────────────────────────────────────────────────────

export interface BehavioralSignals {
  preferred_bloom_level: string | null
  struggle_bloom_level: string | null
  avg_session_duration_ms: number
  sessions_per_day: number
  question_complexity_trend: 'rising' | 'stable' | 'declining'
  dominant_subject: string | null
  total_sessions: number
  total_misconceptions: number
  engagement_streak: number
  strengths: string[]
  recent_topics: string[]
  response_pattern: 'procedural' | 'conceptual' | 'mixed' | 'unknown'
}

export interface StudentProfile {
  id: string
  user_id: string
  institution: string | null
  grade: string | null
  subjects: string[]
  current_chapter: string | null
  learning_velocity: number
  confidence_score: number
  behavioral_signals: BehavioralSignals
  last_active: string
  created_at: string
  updated_at: string
}

export interface MasteryRecord {
  id: string
  concept_id: string
  concept_name: string
  score: number
  label: 'mastered' | 'developing' | 'emerging' | 'not_started'
  interaction_count: number
  last_updated: string
}

export interface Recommendation {
  concept_id: string
  concept_name: string
  subject: string | null
  chapter: string | null
  reason: string
  readiness_score: number
}

export interface LearningAnalytics {
  user_id: string
  total_sessions: number
  total_concepts_encountered: number
  average_mastery: number
  mastered_count: number
  developing_count: number
  emerging_count: number
  not_started_count: number
  active_gaps: number
  critical_gaps: number
  recent_bloom_levels: Record<string, number>
  recent_concepts: string[]
  velocity_trend: number
}
