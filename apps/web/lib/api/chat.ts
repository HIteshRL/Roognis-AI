import type { ConversationDto, ConversationWithMessagesDto, SubjectCountDto } from '@roognis/shared'
import { apiClient } from './client'

export const chatApi = {
  sendMessage: (
    message: string,
    conversationId?: string,
    subject?: string,
    chapter?: string,
  ) =>
    apiClient.streamPost('/api/v1/chat', {
      message,
      conversation_id: conversationId,
      subject: subject || undefined,
      chapter: chapter || undefined,
    }),

  listConversations: (page = 1, limit = 20, subject?: string) => {
    let url = `/api/v1/chat/history?page=${page}&limit=${limit}`
    if (subject !== undefined) {
      url += `&subject=${encodeURIComponent(subject)}`
    }
    return apiClient.get<ConversationDto[]>(url)
  },

  getSubjects: () => apiClient.get<SubjectCountDto[]>('/api/v1/chat/subjects'),

  getConversation: (id: string) =>
    apiClient.get<ConversationWithMessagesDto>(`/api/v1/chat/history/${id}`),

  deleteConversation: (id: string) => apiClient.delete<void>(`/api/v1/chat/history/${id}`),
}
