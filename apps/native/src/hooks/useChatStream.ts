import { useCallback } from 'react'
import type { MessageDto } from '@/types'
import { chatApi, streamMessage } from '@/api/chat'
import { useChatStore } from '@/store/chat.store'

/**
 * Sends a chat message and consumes the SSE stream, updating the chat store.
 * Reads/writes the store via getState() so the callback stays stable and never
 * closes over stale state (matches the web useChat lifecycle).
 */
export function useChatStream() {
  const send = useCallback(async (rawText: string) => {
    const s = useChatStore.getState()
    const text = rawText.trim()
    if (!text || s.streaming?.isStreaming) return

    const isNew = !s.activeConversationId

    const optimistic: MessageDto = {
      id: `tmp-${Date.now()}`,
      conversation_id: s.activeConversationId ?? '',
      role: 'user',
      content: text,
      token_count: null,
      created_at: new Date().toISOString(),
    }
    s.setMessages([...s.messages, optimistic])
    s.startStreaming()

    let newConversationId: string | null = null

    try {
      await streamMessage(
        {
          message: text,
          conversationId: s.activeConversationId ?? undefined,
          subject: isNew ? (s.pendingSubject ?? undefined) : undefined,
          chapter: isNew ? (s.pendingChapter ?? undefined) : undefined,
        },
        (event) => {
          if (event.type === 'meta' && event.conversation_id) {
            newConversationId = event.conversation_id
            if (event.rag?.sources) useChatStore.getState().setSources(event.rag.sources)
          } else if (event.type === 'chunk' && event.content) {
            useChatStore.getState().appendStreamChunk(event.content)
          } else if (event.type === 'done') {
            useChatStore.getState().finalizeStreaming()
          }
        },
      )

      const convId = newConversationId ?? s.activeConversationId
      if (convId) {
        const res = await chatApi.getConversation(convId)
        useChatStore.getState().setActiveConversation(convId)
        useChatStore.getState().setMessages(res.data.messages)
      }
    } finally {
      useChatStore.getState().finalizeStreaming()
    }
  }, [])

  return { send }
}
