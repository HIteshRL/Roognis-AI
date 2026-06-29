import type { ConversationDto, ConversationWithMessagesDto } from '@roognis/shared'
import { apiClient } from './client'

export const chatApi = {
  sendMessage: (message: string, conversationId?: string) =>
    apiClient.streamPost('/api/v1/chat', { message, conversation_id: conversationId }),

  listConversations: (page = 1, limit = 20) =>
    apiClient.get<ConversationDto[]>(`/api/v1/chat/history?page=${page}&limit=${limit}`),

  getConversation: (id: string) =>
    apiClient.get<ConversationWithMessagesDto>(`/api/v1/chat/history/${id}`),

  deleteConversation: (id: string) => apiClient.delete<void>(`/api/v1/chat/history/${id}`),
}
