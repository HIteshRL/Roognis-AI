import { apiClient } from './client'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Classroom {
  id: string
  teacher_id: string
  name: string
  subject: string | null
  section: string | null
  room: string | null
  grade: string | null
  description: string | null
  color: string
  join_code: string
  is_archived: boolean
  student_count: number
  chapter_count: number
  created_at: string
  updated_at: string
}

export interface Chapter {
  id: string
  classroom_id: string
  knowledge_base_id: string | null
  title: string
  description: string | null
  order_index: number
  is_published: boolean
  document_count: number
  created_at: string
  updated_at: string
}

export interface EnrolledStudent {
  id: string
  username: string
  email: string
  joined_at: string
}

export interface StudentClassroom {
  id: string
  name: string
  subject: string | null
  section: string | null
  grade: string | null
  color: string
  teacher_name: string
  chapter_count: number
  created_at: string
}

export interface CreateClassroomPayload {
  name: string
  subject?: string | null
  section?: string | null
  room?: string | null
  grade?: string | null
  description?: string | null
  color?: string | null
}

export interface CreateChapterPayload {
  title: string
  description?: string | null
}

// ── Teacher API ───────────────────────────────────────────────────────────────

export const teacherApi = {
  listClassrooms: () => apiClient.get<Classroom[]>('/api/v1/teacher/classrooms'),

  getClassroom: (id: string) => apiClient.get<Classroom>(`/api/v1/teacher/classrooms/${id}`),

  createClassroom: (payload: CreateClassroomPayload) =>
    apiClient.post<Classroom>('/api/v1/teacher/classrooms', payload),

  updateClassroom: (id: string, payload: Partial<CreateClassroomPayload>) =>
    apiClient.patch<Classroom>(`/api/v1/teacher/classrooms/${id}`, payload),

  archiveClassroom: (id: string) =>
    apiClient.post<Record<string, never>>(`/api/v1/teacher/classrooms/${id}/archive`, {}),

  regenerateCode: (id: string) =>
    apiClient.post<Classroom>(`/api/v1/teacher/classrooms/${id}/regenerate-code`, {}),

  listStudents: (id: string) =>
    apiClient.get<EnrolledStudent[]>(`/api/v1/teacher/classrooms/${id}/students`),

  removeStudent: (id: string, studentId: string) =>
    apiClient.delete<Record<string, never>>(
      `/api/v1/teacher/classrooms/${id}/students/${studentId}`
    ),

  listChapters: (id: string) =>
    apiClient.get<Chapter[]>(`/api/v1/teacher/classrooms/${id}/chapters`),

  addChapter: (id: string, payload: CreateChapterPayload) =>
    apiClient.post<Chapter>(`/api/v1/teacher/classrooms/${id}/chapters`, payload),

  updateChapter: (chapterId: string, payload: Partial<Chapter>) =>
    apiClient.patch<Chapter>(`/api/v1/teacher/chapters/${chapterId}`, payload),

  deleteChapter: (chapterId: string) =>
    apiClient.delete<Record<string, never>>(`/api/v1/teacher/chapters/${chapterId}`),

  uploadContent: (chapterId: string, file: File, title?: string) => {
    const form = new FormData()
    form.append('file', file)
    if (title) form.append('title', title)
    return apiClient.uploadForm<{ id: string; status: string; job_id: string }>(
      `/api/v1/teacher/chapters/${chapterId}/content`,
      form
    )
  },
}

// ── Student API ───────────────────────────────────────────────────────────────

export const classroomStudentApi = {
  joinClass: (joinCode: string) =>
    apiClient.post<StudentClassroom>('/api/v1/student/classrooms/join', {
      join_code: joinCode,
    }),

  listMyClasses: () =>
    apiClient.get<StudentClassroom[]>('/api/v1/student/classrooms'),

  listChapters: (classroomId: string) =>
    apiClient.get<Chapter[]>(`/api/v1/student/classrooms/${classroomId}/chapters`),
}
