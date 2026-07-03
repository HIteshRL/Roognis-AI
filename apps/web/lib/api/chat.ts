import type {
  AttachmentDto,
  ChapterDto,
  ConversationDto,
  ConversationWithMessagesDto,
  MediaJobDto,
  SubjectCountDto,
} from '@roognis/shared'
import { apiClient } from './client'

export const chatApi = {
  sendMessage: (
    message: string,
    conversationId?: string,
    subject?: string,
    chapter?: string,
    attachmentIds?: string[],
  ) =>
    apiClient.streamPost('/api/v1/chat', {
      message,
      conversation_id: conversationId,
      subject: subject || undefined,
      chapter: chapter || undefined,
      attachment_ids: attachmentIds && attachmentIds.length > 0 ? attachmentIds : undefined,
    }),

  uploadAttachment: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiClient.upload<AttachmentDto>('/api/v1/chat/attachments', form)
  },

  fetchAttachmentUrl: (attachmentId: string) =>
    apiClient.fetchBlobUrl(`/api/v1/chat/attachments/${attachmentId}`),

  listConversations: (page = 1, limit = 20, subject?: string) => {
    let url = `/api/v1/chat/history?page=${page}&limit=${limit}`
    if (subject !== undefined) {
      url += `&subject=${encodeURIComponent(subject)}`
    }
    return apiClient.get<ConversationDto[]>(url)
  },

  getSubjects: () => apiClient.get<SubjectCountDto[]>('/api/v1/chat/subjects'),

  getChapters: (subject: string) =>
    apiClient.get<ChapterDto[]>(
      `/api/v1/chat/subjects/${encodeURIComponent(subject)}/chapters`,
    ),

  requestVideo: (messageId: string) =>
    apiClient.post<MediaJobDto>(`/api/v1/chat/messages/${messageId}/video`, {}),

  getMediaJob: (jobId: string) =>
    apiClient.get<MediaJobDto>(`/api/v1/chat/media-jobs/${jobId}`),

  getConversation: (id: string) =>
    apiClient.get<ConversationWithMessagesDto>(`/api/v1/chat/history/${id}`),

  deleteConversation: (id: string) => apiClient.delete<void>(`/api/v1/chat/history/${id}`),
}
