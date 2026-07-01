import { apiClient } from './client'

export interface StudentProfile {
  id: string
  user_id: string
  institution: string | null
  grade: string | null
  subjects: string[]
  current_chapter: string | null
  learning_velocity: number
  confidence_score: number
  last_active: string
  created_at: string
  updated_at: string
}

export interface UpdateProfilePayload {
  institution?: string | null
  grade?: string | null
  subjects?: string[]
  current_chapter?: string | null
}

export interface LearningSession {
  id: string
  user_id: string
  conversation_id: string | null
  subject: string | null
  chapter: string | null
  grade: string | null
  question: string
  primary_concept: string | null
  concepts_discussed: string[]
  bloom_level: string
  difficulty_level: string
  misconceptions: string[]
  token_count: number
  duration_ms: number
  created_at: string
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

export interface LearningGap {
  id: string
  concept_id: string
  concept_name: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  reason: string
  confidence: 'low' | 'medium' | 'high'
  occurrence_count: number
  is_resolved: boolean
  created_at: string
  updated_at: string
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
}

export interface SessionsPage {
  data: LearningSession[]
  total: number
  page: number
  limit: number
}

export const studentApi = {
  getProfile: () => apiClient.get<StudentProfile>('/api/v1/student/profile'),

  updateProfile: (payload: UpdateProfilePayload) =>
    apiClient.post<StudentProfile>('/api/v1/student/profile', payload),

  getSessions: (page = 1, limit = 20) =>
    apiClient.get<SessionsPage>(`/api/v1/student/sessions?page=${page}&limit=${limit}`),

  getMastery: () => apiClient.get<MasteryRecord[]>('/api/v1/student/mastery'),

  getGaps: (includeResolved = false) =>
    apiClient.get<LearningGap[]>(
      `/api/v1/student/gaps?include_resolved=${includeResolved}`
    ),

  resolveGap: (gapId: string) =>
    apiClient.post<{ resolved: boolean }>(`/api/v1/student/gaps/${gapId}/resolve`, {}),

  getRecommendations: () =>
    apiClient.get<Recommendation[]>('/api/v1/student/recommendations'),

  getAnalytics: () => apiClient.get<LearningAnalytics>('/api/v1/student/analytics'),
}
