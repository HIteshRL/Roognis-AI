import { useCallback, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { chatApi } from '@/lib/api/chat'
import { useChatStore } from '@/lib/stores/chat.store'

export function useChat(conversationId?: string) {
  const router = useRouter()
  const bottomRef = useRef<HTMLDivElement>(null)

  const {
    messages,
    streaming,
    activeConversationId,
    pendingSubject,
    pendingChapter,
    setActiveConversation,
    setMessages,
    startStreaming,
    appendStreamChunk,
    finalizeStreaming,
    clearPendingChat,
    setSourceMeta,
  } = useChatStore()

  useEffect(() => {
    if (!conversationId) {
      setMessages([])
      setActiveConversation(null)
      return
    }
    if (conversationId === activeConversationId) return

    chatApi
      .getConversation(conversationId)
      .then((res) => {
        setMessages(res.data.messages)
        setActiveConversation(conversationId)
      })
      .catch(() => toast.error('Could not load conversation'))
  }, [conversationId, activeConversationId, setMessages, setActiveConversation])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, streaming?.content])

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || streaming?.isStreaming) return

      startStreaming()

      try {
        const isNewConversation = !activeConversationId
        const stream = await chatApi.sendMessage(
          content,
          activeConversationId ?? undefined,
          isNewConversation ? (pendingSubject ?? undefined) : undefined,
          isNewConversation ? (pendingChapter ?? undefined) : undefined,
        )
        const reader = stream.getReader()
        let newConversationId: string | null = null

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          if (!value) continue

          for (const line of value.split('\n')) {
            if (!line.startsWith('data: ')) continue
            const raw = line.slice(6).trim()
            if (!raw) continue

            try {
              const event = JSON.parse(raw)
              if (event.type === 'meta' && event.conversation_id) {
                newConversationId = event.conversation_id
                if (event.rag) {
                  setSourceMeta({
                    hasContext: event.rag.has_context,
                    sourceCount: event.rag.source_count,
                    cascadeLevel: event.rag.cascade_level ?? 'none',
                    sources: event.rag.sources ?? [],
                  })
                }
              } else if (event.type === 'chunk' && event.content) {
                appendStreamChunk(event.content)
              } else if (event.type === 'done') {
                finalizeStreaming()
              }
            } catch {
              // Partial JSON — skip
            }
          }
        }

        if (newConversationId && newConversationId !== activeConversationId) {
          setActiveConversation(newConversationId)
          clearPendingChat()
          router.push(`/chat/${newConversationId}`)
        } else if (activeConversationId) {
          const res = await chatApi.getConversation(activeConversationId)
          setMessages(res.data.messages)
        }
      } catch {
        finalizeStreaming()
        toast.error('Failed to send message')
      }
    },
    [
      activeConversationId,
      streaming,
      pendingSubject,
      pendingChapter,
      startStreaming,
      appendStreamChunk,
      finalizeStreaming,
      setActiveConversation,
      setMessages,
      clearPendingChat,
      setSourceMeta,
      router,
    ]
  )

  return { messages, streaming, sendMessage, bottomRef }
}
