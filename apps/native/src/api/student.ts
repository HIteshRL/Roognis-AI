import type {
  LearningAnalytics,
  MasteryRecord,
  Recommendation,
  StudentProfile,
} from '@/types'
import { apiClient } from './client'

export const studentApi = {
  getProfile: () => apiClient.get<StudentProfile>('/api/v1/student/profile'),

  updateProfile: (payload: {
    institution?: string | null
    grade?: string | null
    subjects?: string[]
    current_chapter?: string | null
  }) => apiClient.post<StudentProfile>('/api/v1/student/profile', payload),

  getMastery: () => apiClient.get<MasteryRecord[]>('/api/v1/student/mastery'),

  getAnalytics: () => apiClient.get<LearningAnalytics>('/api/v1/student/analytics'),

  getRecommendations: () =>
    apiClient.get<Recommendation[]>('/api/v1/student/recommendations'),
}
