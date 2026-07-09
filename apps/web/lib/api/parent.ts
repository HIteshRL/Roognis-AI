import { apiClient } from './client'

export interface LinkCode {
  code: string
  expires_in_seconds: number
}

export interface Guardian {
  link_id: string
  parent_id: string
  username: string
  email: string
  linked_at: string
}

export interface Child {
  link_id: string
  student_id: string
  username: string
  email: string
  grade: string | null
  linked_at: string
}

export interface ChildOverview {
  student_id: string
  username: string
  grade: string | null
  average_mastery: number
  mastered_count: number
  total_concepts: number
  active_gaps: number
  total_sessions: number
  engagement_streak: number
  strengths: string[]
  weak_areas: { concept: string; severity: string }[]
  recent_activity: { question: string; subject: string | null; created_at: string }[]
}

export const parentApi = {
  // Student side
  issueLinkCode: () => apiClient.post<LinkCode>('/api/v1/parent/link-code', {}),
  getGuardians: () => apiClient.get<Guardian[]>('/api/v1/parent/guardians'),
  revokeGuardian: (parentId: string) =>
    apiClient.delete<{ revoked: boolean }>(`/api/v1/parent/guardians/${parentId}`),

  // Parent side
  linkChild: (code: string) =>
    apiClient.post<{ student_id: string; username: string }>('/api/v1/parent/link', {
      code,
    }),
  getChildren: () => apiClient.get<Child[]>('/api/v1/parent/children'),
  getChildOverview: (studentId: string) =>
    apiClient.get<ChildOverview>(`/api/v1/parent/children/${studentId}/overview`),
}
