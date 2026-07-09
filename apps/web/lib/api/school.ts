import { apiClient } from './client'

export interface School {
  id: string
  name: string
  slug: string
  address: string | null
  is_active: boolean
  my_role: 'teacher' | 'school_admin'
  created_at: string
  updated_at: string
}

export interface SchoolMember {
  id: string
  user_id: string
  email: string
  username: string
  role: string
  status: string
}

export interface Classroom {
  id: string
  school_id: string
  name: string
  subject: string | null
  grade: string | null
  teacher_id: string | null
  join_code: string
  description: string | null
  is_active: boolean
  knowledge_base_id: string | null
  material_count: number
  student_count: number
  syllabus_count: number
  created_at: string
  updated_at: string
}

export interface Material {
  id: string
  classroom_id: string
  filename: string
  title: string | null
  chapter: string | null
  file_type: string
  file_size: number
  status: 'pending' | 'processing' | 'ready' | 'failed'
  chunk_count: number
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface MaterialUpload {
  id: string
  classroom_id: string
  filename: string
  status: string
  job_id: string
  created_at: string
}

export interface RosterEntry {
  enrollment_id: string
  student_id: string
  username: string
  email: string
  status: string
  enrolled_at: string
}

export interface SyllabusItem {
  id: string
  classroom_id: string
  subject: string
  chapter: string
  topic: string | null
  description: string | null
  order_index: number
  knowledge_base_id: string | null
  is_published: boolean
  created_at: string
  updated_at: string
}

export interface StudentAnalyticsEntry {
  student_id: string
  username: string
  email: string
  avg_mastery: number
  active_gap_count: number
  session_count: number
  last_activity: string | null
}

export interface MasteryBucket {
  label: string
  count: number
}

export interface MisconceptionConcept {
  concept_name: string
  student_count: number
}

export interface ClassroomAnalytics {
  classroom_id: string
  student_count: number
  total_sessions: number
  class_avg_mastery: number
  mastery_distribution: MasteryBucket[]
  top_misconceptions: MisconceptionConcept[]
  students: StudentAnalyticsEntry[]
}

export interface CreateClassroomPayload {
  school_id: string
  name: string
  subject?: string | null
  grade?: string | null
  description?: string | null
}

export interface CreateSyllabusPayload {
  subject: string
  chapter: string
  topic?: string | null
  description?: string | null
  order_index?: number
  knowledge_base_id?: string | null
  is_published?: boolean
}

export const schoolApi = {
  // ── Schools ────────────────────────────────────────────────────────────
  createSchool: (name: string, address?: string | null) =>
    apiClient.post<School>('/api/v1/school/schools', { name, address }),

  getMySchools: () => apiClient.get<School[]>('/api/v1/school/schools/mine'),

  addTeacher: (schoolId: string, email: string, role = 'teacher') =>
    apiClient.post<SchoolMember>(`/api/v1/school/schools/${schoolId}/teachers`, {
      email,
      role,
    }),

  getMembers: (schoolId: string) =>
    apiClient.get<SchoolMember[]>(`/api/v1/school/schools/${schoolId}/members`),

  // ── Classrooms (teacher) ───────────────────────────────────────────────
  createClassroom: (payload: CreateClassroomPayload) =>
    apiClient.post<Classroom>('/api/v1/school/classrooms', payload),

  getMyClassrooms: () =>
    apiClient.get<Classroom[]>('/api/v1/school/classrooms/mine'),

  getClassroom: (id: string) =>
    apiClient.get<Classroom>(`/api/v1/school/classrooms/${id}`),

  updateClassroom: (id: string, payload: Partial<CreateClassroomPayload> & { is_active?: boolean }) =>
    apiClient.patch<Classroom>(`/api/v1/school/classrooms/${id}`, payload),

  deleteClassroom: (id: string) =>
    apiClient.delete<{ deleted: boolean }>(`/api/v1/school/classrooms/${id}`),

  getRoster: (id: string) =>
    apiClient.get<RosterEntry[]>(`/api/v1/school/classrooms/${id}/roster`),

  getClassroomAnalytics: (id: string) =>
    apiClient.get<ClassroomAnalytics>(`/api/v1/school/classrooms/${id}/analytics`),

  // ── Materials (teacher uploads → student RAG) ──────────────────────────
  getMaterials: (classroomId: string) =>
    apiClient.get<Material[]>(`/api/v1/school/classrooms/${classroomId}/materials`),

  uploadMaterial: (classroomId: string, file: File, chapter?: string) => {
    const form = new FormData()
    form.append('file', file)
    const qs = chapter ? `?chapter=${encodeURIComponent(chapter)}` : ''
    return apiClient.upload<MaterialUpload>(
      `/api/v1/school/classrooms/${classroomId}/materials${qs}`,
      form
    )
  },

  deleteMaterial: (classroomId: string, documentId: string) =>
    apiClient.delete<Record<string, never>>(
      `/api/v1/school/classrooms/${classroomId}/materials/${documentId}`
    ),

  // ── Syllabus ───────────────────────────────────────────────────────────
  getSyllabus: (classroomId: string) =>
    apiClient.get<SyllabusItem[]>(`/api/v1/school/classrooms/${classroomId}/syllabus`),

  addSyllabusItem: (classroomId: string, payload: CreateSyllabusPayload) =>
    apiClient.post<SyllabusItem>(
      `/api/v1/school/classrooms/${classroomId}/syllabus`,
      payload
    ),

  updateSyllabusItem: (itemId: string, payload: Partial<CreateSyllabusPayload>) =>
    apiClient.patch<SyllabusItem>(`/api/v1/school/syllabus/${itemId}`, payload),

  deleteSyllabusItem: (itemId: string) =>
    apiClient.delete<{ deleted: boolean }>(`/api/v1/school/syllabus/${itemId}`),

  // ── Student ────────────────────────────────────────────────────────────
  joinClassroom: (joinCode: string) =>
    apiClient.post<Classroom>('/api/v1/school/classrooms/join', {
      join_code: joinCode,
    }),

  getEnrolledClassrooms: () =>
    apiClient.get<Classroom[]>('/api/v1/school/classrooms/enrolled/mine'),
}
