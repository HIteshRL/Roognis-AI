import { create } from 'zustand'
import type { MessageDto, StreamSourceDto } from '@/types'

interface Streaming {
  content: string
  isStreaming: boolean
}

interface ChatState {
  activeConversationId: string | null
  messages: MessageDto[]
  streaming: Streaming | null
  sources: StreamSourceDto[]
  pendingSubject: string | null
  pendingChapter: string | null

  setActiveConversation: (id: string | null) => void
  setMessages: (msgs: MessageDto[]) => void
  startStreaming: () => void
  appendStreamChunk: (chunk: string) => void
  finalizeStreaming: () => void
  setSources: (sources: StreamSourceDto[]) => void
  setPendingChat: (subject: string | null, chapter: string | null) => void
  resetConversation: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  activeConversationId: null,
  messages: [],
  streaming: null,
  sources: [],
  pendingSubject: null,
  pendingChapter: null,

  setActiveConversation: (id) => set({ activeConversationId: id }),
  setMessages: (messages) => set({ messages }),

  startStreaming: () => set({ streaming: { content: '', isStreaming: true }, sources: [] }),

  appendStreamChunk: (chunk) =>
    set((s) => ({
      streaming: {
        content: (s.streaming?.content ?? '') + chunk,
        isStreaming: true,
      },
    })),

  finalizeStreaming: () =>
    set((s) => ({ streaming: s.streaming ? { ...s.streaming, isStreaming: false } : null })),

  setSources: (sources) => set({ sources }),

  setPendingChat: (pendingSubject, pendingChapter) => set({ pendingSubject, pendingChapter }),

  resetConversation: () =>
    set({ activeConversationId: null, messages: [], streaming: null, sources: [] }),
}))
