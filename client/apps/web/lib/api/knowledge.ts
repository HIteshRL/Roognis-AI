import { apiClient } from './client'

export interface KnowledgeBase {
  id: string
  name: string
  description: string | null
  institution: string | null
  subject: string | null
  language: string
  is_active: boolean
  document_count: number
  created_at: string
  updated_at: string
}

export interface Document {
  id: string
  knowledge_base_id: string
  filename: string
  title: string | null
  file_type: string
  file_size: number
  status: 'pending' | 'processing' | 'ready' | 'failed'
  chunk_count: number
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface Chunk {
  id: string
  document_id: string
  chunk_index: number
  content: string
  token_count: number
  page_number: number | null
  metadata: Record<string, unknown>
}

export interface IngestionJob {
  id: string
  document_id: string
  status: string
  progress: number
  error_message: string | null
  created_at: string
  updated_at: string
}

export const knowledgeApi = {
  listKnowledgeBases: (page = 1, limit = 20) =>
    apiClient.get<KnowledgeBase[]>(`/api/v1/library?page=${page}&limit=${limit}`),

  createKnowledgeBase: (data: { name: string; description?: string; institution?: string; subject?: string }) =>
    apiClient.post<KnowledgeBase>('/api/v1/library', data),

  getKnowledgeBase: (id: string) => apiClient.get<KnowledgeBase>(`/api/v1/library/${id}`),

  deleteKnowledgeBase: (id: string) => apiClient.delete<void>(`/api/v1/library/${id}`),

  listDocuments: (kbId: string, page = 1, limit = 20) =>
    apiClient.get<Document[]>(`/api/v1/documents/${kbId}?page=${page}&limit=${limit}`),

  getDocument: (kbId: string, docId: string) =>
    apiClient.get<Document>(`/api/v1/documents/${kbId}/${docId}`),

  deleteDocument: (kbId: string, docId: string) =>
    apiClient.delete<void>(`/api/v1/documents/${kbId}/${docId}`),

  getChunks: (kbId: string, docId: string) =>
    apiClient.get<Chunk[]>(`/api/v1/documents/${kbId}/${docId}/chunks`),

  getJobStatus: (kbId: string, docId: string) =>
    apiClient.get<IngestionJob>(`/api/v1/documents/${kbId}/${docId}/status`),

  reindex: (kbId: string, docId: string) =>
    apiClient.post<void>(`/api/v1/documents/${kbId}/${docId}/reindex`, {}),

  uploadDocument: async (kbId: string, file: File, token: string) => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/v1/documents/upload/${kbId}`,
      { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: formData }
    )
    const json = await res.json()
    if (!res.ok) throw new Error(json.error?.message ?? 'Upload failed')
    return json
  },
}
