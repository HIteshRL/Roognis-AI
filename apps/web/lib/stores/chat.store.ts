import { create } from 'zustand'
import type { ConversationDto, MessageDto } from '@roognis/shared'

interface StreamingMessage {
  content: string
  isStreaming: boolean
}

interface ChatState {
  activeConversationId: string | null
  conversations: ConversationDto[]
  messages: MessageDto[]
  streaming: StreamingMessage | null

  setActiveConversation: (id: string | null) => void
  setConversations: (convs: ConversationDto[]) => void
  setMessages: (msgs: MessageDto[]) => void
  appendConversation: (conv: ConversationDto) => void
  removeConversation: (id: string) => void
  startStreaming: () => void
  appendStreamChunk: (chunk: string) => void
  finalizeStreaming: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  activeConversationId: null,
  conversations: [],
  messages: [],
  streaming: null,

  setActiveConversation: (id) => set({ activeConversationId: id }),
  setConversations: (conversations) => set({ conversations }),
  setMessages: (messages) => set({ messages }),

  appendConversation: (conv) =>
    set((s) => ({ conversations: [conv, ...s.conversations.filter((c) => c.id !== conv.id)] })),

  removeConversation: (id) =>
    set((s) => ({ conversations: s.conversations.filter((c) => c.id !== id) })),

  startStreaming: () => set({ streaming: { content: '', isStreaming: true } }),

  appendStreamChunk: (chunk) =>
    set((s) => ({
      streaming: s.streaming
        ? { content: s.streaming.content + chunk, isStreaming: true }
        : { content: chunk, isStreaming: true },
    })),

  finalizeStreaming: () =>
    set((s) => ({
      streaming: s.streaming ? { ...s.streaming, isStreaming: false } : null,
    })),
}))
