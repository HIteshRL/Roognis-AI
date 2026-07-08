'use client'

import { useEffect, useState } from 'react'
import { PenSquare, Sparkles } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { chatApi } from '@/lib/api/chat'
import { studentApi } from '@/lib/api/student'
import { useChatStore } from '@/lib/stores/chat.store'
import { useChat } from '../hooks/useChat'
import { ChatInput } from './ChatInput'
import { ChatWelcome } from './ChatWelcome'
import { MessageBubble } from './MessageBubble'
import { SubjectList } from './SubjectList'
import { ConversationList } from './ConversationList'
import { NewChatDialog } from './NewChatDialog'
import { SourceCitation } from './SourceCitation'
import { StreamingMessage } from './StreamingMessage'
import { TypingIndicator } from './TypingIndicator'

interface ChatViewProps {
  conversationId?: string
}

export function ChatView({ conversationId }: ChatViewProps) {
  const [showNewChat, setShowNewChat] = useState(false)
  const selectedSubject = useChatStore((s) => s.selectedSubject)
  const setSelectedSubject = useChatStore((s) => s.setSelectedSubject)
  const setConversations = useChatStore((s) => s.setConversations)
  const pendingSubject = useChatStore((s) => s.pendingSubject)
  const pendingChapter = useChatStore((s) => s.pendingChapter)

  const { data: subjectCounts } = useQuery({
    queryKey: ['chat-subjects'],
    queryFn: () => chatApi.getSubjects(),
    select: (r) => r.data,
  })

  const { data: profile } = useQuery({
    queryKey: ['student-profile'],
    queryFn: () => studentApi.getProfile(),
    select: (r) => r.data,
  })

  const subjectFilter = selectedSubject === 'General' ? '' : (selectedSubject ?? undefined)
  const { data: historyData } = useQuery({
    queryKey: ['conversations', selectedSubject],
    queryFn: () => chatApi.listConversations(1, 50, subjectFilter),
    select: (r) => r.data,
  })

  useEffect(() => {
    if (historyData) setConversations(historyData as any)
  }, [historyData, setConversations])

  const { messages, streaming, sendMessage, bottomRef } = useChat(conversationId)
  const conversations = useChatStore((s) => s.conversations)
  const lastSourceMeta = useChatStore((s) => s.lastSourceMeta)
  const isStreaming = streaming?.isStreaming ?? false

  const activeConv = conversations.find((c) => c.id === conversationId)
  const currentSubject = pendingSubject ?? activeConv?.subject
  const currentChapter = pendingChapter ?? activeConv?.chapter

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left panel — two-level navigation */}
      <aside className="flex h-full w-[280px] flex-col border-r border-border bg-sidebar">
        <div className="flex h-12 items-center justify-between px-3">
          <span className="text-sm font-medium">
            {selectedSubject !== null ? 'Conversations' : 'Subjects'}
          </span>
          <button
            onClick={() => setShowNewChat(!showNewChat)}
            className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
            aria-label="New conversation"
          >
            <PenSquare className="h-4 w-4" />
          </button>
        </div>
        <Separator />

        <ScrollArea className="flex-1 py-2">
          {selectedSubject !== null ? (
            <ConversationList
              conversations={conversations}
              subjectLabel={selectedSubject}
              onBack={() => setSelectedSubject(null)}
            />
          ) : (
            <SubjectList
              subjects={profile?.subjects ?? []}
              subjectCounts={subjectCounts ?? []}
              selectedSubject={selectedSubject}
              onSelect={setSelectedSubject}
            />
          )}
        </ScrollArea>

        {/* New chat panel (slides in at bottom) */}
        <NewChatDialog
          subjects={profile?.subjects ?? []}
          open={showNewChat}
          onClose={() => setShowNewChat(false)}
        />
      </aside>

      {/* Chat window */}
      <div className="relative flex flex-1 flex-col overflow-hidden bg-background">
        <div className="aurora" aria-hidden />

        {/* Header */}
        <div className="relative z-10 flex h-14 items-center gap-2 border-b border-border/60 px-5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-sky-500 shadow-sm shadow-primary/30">
            <Sparkles className="h-3.5 w-3.5 text-white" />
          </div>
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-sm font-semibold leading-tight">
              {currentSubject ?? 'Roognis Tutor'}
            </span>
            {currentChapter && (
              <span className="truncate text-[11px] leading-tight text-muted-foreground">
                {currentChapter}
              </span>
            )}
          </div>
          {currentSubject && (
            <Badge variant="secondary" className="ml-auto gap-1 text-[10px]">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Curriculum-scoped
            </Badge>
          )}
        </div>

        <ScrollArea className="relative z-10 flex-1">
          {messages.length === 0 && !streaming ? (
            <div className="h-[calc(100vh-8.5rem)]">
              <ChatWelcome subject={currentSubject} chapter={currentChapter} onPick={sendMessage} />
            </div>
          ) : (
            <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-6">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {streaming && (
                streaming.isStreaming && !streaming.content ? (
                  <TypingIndicator />
                ) : (
                  <>
                    <StreamingMessage content={streaming.content} isStreaming={streaming.isStreaming} />
                    {!streaming.isStreaming && lastSourceMeta && lastSourceMeta.sources.length > 0 && (
                      <SourceCitation
                        sources={lastSourceMeta.sources}
                        cascadeLevel={lastSourceMeta.cascadeLevel}
                      />
                    )}
                  </>
                )
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </ScrollArea>

        {/* Input */}
        <div className="relative z-10 px-4 pb-4 pt-2">
          <div className="mx-auto max-w-3xl">
            <ChatInput onSend={sendMessage} disabled={isStreaming} />
            <p className="mt-2 text-center text-[11px] text-muted-foreground/70">
              Roognis may make mistakes. Verify important information.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
