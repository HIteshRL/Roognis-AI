import { apiClient } from './client'

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
  intent: 'concept_explanation' | 'problem_solving' | 'clarification' | 'recall' | 'test_prep' | 'correction_request' | 'unknown'
  token_count: number
  duration_ms: number
  created_at: string
}

export interface ConceptMemory {
  id: string
  concept_id: string
  concept_name: string
  times_taught: number
  successful_approaches: number
  failed_approaches: number
  last_approach: string | null
  teaching_notes: string[]
  success_rate: number
  needs_different_approach: boolean
  last_taught: string
}

export interface LearningPathNode {
  concept_id: string
  concept_name: string
  subject: string | null
  chapter: string | null
  bloom_level: string
  difficulty: string
}

export interface LearningPath {
  target_concept_id: string | null
  path: LearningPathNode[]
  frontier: Recommendation[]
  coverage: Record<string, { total: number; mastered: number; coverage_pct: number }>
}

export interface SkillEntry {
  skill: string
  proficiency: number
}

export interface SkillProfile {
  skill_profile: Record<string, number>
  top_skills: SkillEntry[]
  bloom_distribution: Record<string, number>
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
  velocity_trend: number
  at_risk_concepts: RetentionRisk[]
}

export interface RetentionRisk {
  concept_id: string
  concept_name: string
  score: number
  days_since_reinforced: number
  risk: number
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

  getConceptMemory: () => apiClient.get<ConceptMemory[]>('/api/v1/student/memory'),

  getLearningPath: (targetConceptId?: string) =>
    apiClient.get<LearningPath>(
      `/api/v1/student/learning-path${targetConceptId ? `?target_concept_id=${targetConceptId}` : ''}`
    ),

  getSkillProfile: () => apiClient.get<SkillProfile>('/api/v1/student/skills'),

  // ── Quiz & Assessment ───────────────────────────────────────────────────

  generateQuiz: (body: {
    subject?: string | null
    chapter?: string | null
    concept_ids?: string[] | null
    question_count?: number
    difficulty?: string
  }) => apiClient.post<import('@roognis/shared').QuizSummaryDto>('/api/v1/student/quiz/generate', body),

  getQuizzes: (page = 1, limit = 20, subject?: string) =>
    apiClient.get<{ data: import('@roognis/shared').QuizSummaryDto[]; pagination: { total: number; page: number; limit: number } }>(
      `/api/v1/student/quiz?page=${page}&limit=${limit}${subject ? `&subject=${encodeURIComponent(subject)}` : ''}`
    ),

  getQuiz: (quizId: string) =>
    apiClient.get<import('@roognis/shared').QuizDetailDto>(`/api/v1/student/quiz/${quizId}`),

  submitQuiz: (quizId: string, responses: import('@roognis/shared').SubmitResponseDto[]) =>
    apiClient.post<import('@roognis/shared').QuizAttemptDto>(`/api/v1/student/quiz/${quizId}/submit`, { responses }),

  getAttemptResults: (attemptId: string) =>
    apiClient.get<import('@roognis/shared').QuizResultDto>(`/api/v1/student/quiz/attempts/${attemptId}/results`),

  getQuizHistory: (limit = 10) =>
    apiClient.get<import('@roognis/shared').QuizHistoryItemDto[]>(`/api/v1/student/quiz/history?limit=${limit}`),
}
