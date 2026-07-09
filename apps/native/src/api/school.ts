import { apiClient } from './client'

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
  student_count: number
  syllabus_count: number
  created_at: string
  updated_at: string
}

export interface School {
  id: string
  name: string
  slug: string
  address: string | null
  is_active: boolean
  my_role: string
  created_at: string
  updated_at: string
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

export interface RosterEntry {
  enrollment_id: string
  student_id: string
  username: string
  email: string
  status: string
  enrolled_at: string
}

export const schoolApi = {
  // Student
  joinClassroom: (joinCode: string) =>
    apiClient.post<Classroom>('/api/v1/school/classrooms/join', { join_code: joinCode }),

  getEnrolled: () =>
    apiClient.get<Classroom[]>('/api/v1/school/classrooms/enrolled/mine'),

  getSyllabus: (classroomId: string) =>
    apiClient.get<SyllabusItem[]>(`/api/v1/school/classrooms/${classroomId}/syllabus`),

  // Teacher
  getMySchools: () => apiClient.get<School[]>('/api/v1/school/schools/mine'),

  createSchool: (name: string) =>
    apiClient.post<School>('/api/v1/school/schools', { name }),

  getMyClassrooms: () =>
    apiClient.get<Classroom[]>('/api/v1/school/classrooms/mine'),

  createClassroom: (payload: {
    school_id: string
    name: string
    subject?: string | null
    grade?: string | null
  }) => apiClient.post<Classroom>('/api/v1/school/classrooms', payload),

  getRoster: (classroomId: string) =>
    apiClient.get<RosterEntry[]>(`/api/v1/school/classrooms/${classroomId}/roster`),

  addSyllabusItem: (
    classroomId: string,
    payload: { subject: string; chapter: string; topic?: string | null; is_published?: boolean },
  ) => apiClient.post<SyllabusItem>(`/api/v1/school/classrooms/${classroomId}/syllabus`, payload),

  toggleSyllabusPublish: (itemId: string, isPublished: boolean) =>
    apiClient.patch<SyllabusItem>(`/api/v1/school/syllabus/${itemId}`, {
      is_published: isPublished,
    }),
}
