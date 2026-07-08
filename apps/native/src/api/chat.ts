import { fetch as streamFetch } from 'expo/fetch'
import type {
  ChapterDto,
  ChatStreamEvent,
  ConversationDto,
  ConversationWithMessagesDto,
  SubjectCountDto,
} from '@/types'
import { apiClient, authHeaders, getApiBase } from './client'

export interface SendMessagePayload {
  message: string
  conversationId?: string
  subject?: string
  chapter?: string
}

export const chatApi = {
  listConversations: (page = 1, limit = 20, subject?: string) => {
    let url = `/api/v1/chat/history?page=${page}&limit=${limit}`
    if (subject !== undefined) url += `&subject=${encodeURIComponent(subject)}`
    return apiClient.get<ConversationDto[]>(url)
  },

  getSubjects: () => apiClient.get<SubjectCountDto[]>('/api/v1/chat/subjects'),

  getChapters: (subject: string) =>
    apiClient.get<ChapterDto[]>(`/api/v1/chat/subjects/${encodeURIComponent(subject)}/chapters`),

  getConversation: (id: string) =>
    apiClient.get<ConversationWithMessagesDto>(`/api/v1/chat/history/${id}`),

  deleteConversation: (id: string) => apiClient.del<void>(`/api/v1/chat/history/${id}`),
}

/**
 * Streams POST /api/v1/chat as Server-Sent Events using expo/fetch (whose
 * Response.body is a real ReadableStream, unlike React Native's global fetch).
 * Mirrors the web useChat parser: line-buffered, only "data: " lines, JSON per event.
 */
export async function streamMessage(
  payload: SendMessagePayload,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await streamFetch(`${getApiBase()}/api/v1/chat`, {
    method: 'POST',
    headers: authHeaders({ Accept: 'text/event-stream' }),
    body: JSON.stringify({
      message: payload.message,
      conversation_id: payload.conversationId,
      subject: payload.subject || undefined,
      chapter: payload.chapter || undefined,
    }),
    signal,
  })

  if (!res.ok || !res.body) {
    throw new Error(`Stream request failed: ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const lines = buffer.split('\n')
    // Keep the last (possibly partial) line in the buffer.
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const raw = line.slice(6).trim()
      if (!raw) continue
      try {
        onEvent(JSON.parse(raw) as ChatStreamEvent)
      } catch {
        // Partial / non-JSON frame — skip.
      }
    }
  }
}
