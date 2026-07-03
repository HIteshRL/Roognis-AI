import { create } from 'zustand'
import type { ConversationDto, MessageDto, StreamSourceDto } from '@roognis/shared'

interface StreamingMessage {
  content: string
  isStreaming: boolean
}

interface SourceMeta {
  hasContext: boolean
  sourceCount: number
  cascadeLevel: string
  sources: StreamSourceDto[]
}

interface ChatState {
  activeConversationId: string | null
  conversations: ConversationDto[]
  messages: MessageDto[]
  streaming: StreamingMessage | null
  lastSourceMeta: SourceMeta | null
  streamingImageId: string | null

  selectedSubject: string | null
  pendingSubject: string | null
  pendingChapter: string | null

  setActiveConversation: (id: string | null) => void
  setConversations: (convs: ConversationDto[]) => void
  setMessages: (msgs: MessageDto[]) => void
  appendConversation: (conv: ConversationDto) => void
  removeConversation: (id: string) => void
  startStreaming: () => void
  appendStreamChunk: (chunk: string) => void
  finalizeStreaming: () => void
  setSourceMeta: (meta: SourceMeta) => void
  setStreamingImageId: (id: string | null) => void

  setSelectedSubject: (subject: string | null) => void
  setPendingChat: (subject: string | null, chapter: string | null) => void
  clearPendingChat: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  activeConversationId: null,
  conversations: [],
  messages: [],
  streaming: null,
  lastSourceMeta: null,
  streamingImageId: null,

  selectedSubject: null,
  pendingSubject: null,
  pendingChapter: null,

  setActiveConversation: (id) => set({ activeConversationId: id }),
  setConversations: (conversations) => set({ conversations }),
  setMessages: (messages) => set({ messages }),

  appendConversation: (conv) =>
    set((s) => ({ conversations: [conv, ...s.conversations.filter((c) => c.id !== conv.id)] })),

  removeConversation: (id) =>
    set((s) => ({ conversations: s.conversations.filter((c) => c.id !== id) })),

  startStreaming: () =>
    set({ streaming: { content: '', isStreaming: true }, lastSourceMeta: null, streamingImageId: null }),

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

  setSourceMeta: (meta) => set({ lastSourceMeta: meta }),
  setStreamingImageId: (id) => set({ streamingImageId: id }),

  setSelectedSubject: (subject) => set({ selectedSubject: subject }),
  setPendingChat: (subject, chapter) => set({ pendingSubject: subject, pendingChapter: chapter }),
  clearPendingChat: () => set({ pendingSubject: null, pendingChapter: null }),
}))
