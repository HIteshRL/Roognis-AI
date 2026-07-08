'use client'

import { useQuery } from '@tanstack/react-query'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { chatApi } from '@/lib/api/chat'
import { studentApi } from '@/lib/api/student'
import { useChatStore } from '@/lib/stores/chat.store'
import type { AttachmentDto } from '@roognis/shared'
import { Sparkles } from 'lucide-react'
import { useChat } from '../hooks/useChat'
import { AttachmentImage } from './AttachmentImage'
import { ChatInput } from './ChatInput'
import { ChatWelcome } from './ChatWelcome'
import { ContextPanel } from './ContextPanel'
import { MessageBubble } from './MessageBubble'
import { StreamingMessage } from './StreamingMessage'
import { SubjectChapterRail } from './SubjectChapterRail'
import { TypingIndicator } from './TypingIndicator'

interface ClassroomChatViewProps {
  conversationId?: string
}

export function ClassroomChatView({ conversationId }: ClassroomChatViewProps) {
  const pendingSubject = useChatStore((s) => s.pendingSubject)
  const pendingChapter = useChatStore((s) => s.pendingChapter)
  const conversations = useChatStore((s) => s.conversations)
  const streamingImageId = useChatStore((s) => s.streamingImageId)

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

  const { data: analytics } = useQuery({
    queryKey: ['student-analytics'],
    queryFn: () => studentApi.getAnalytics(),
    select: (r) => r.data,
  })

  const { messages, streaming, sendMessage, bottomRef } = useChat(conversationId)
  const isStreaming = streaming?.isStreaming ?? false

  const activeConv = conversations.find((c) => c.id === conversationId)
  const currentSubject = pendingSubject ?? activeConv?.subject
  const currentChapter = pendingChapter ?? activeConv?.chapter

  const streamingImage: AttachmentDto | null = streamingImageId
    ? {
        id: streamingImageId,
        kind: 'image',
        content_type: 'image/*',
        file_size: 0,
        url: `/api/v1/chat/attachments/${streamingImageId}`,
        created_at: '',
      }
    : null

  return (
    <div className="flex h-full overflow-hidden">
      <SubjectChapterRail
        subjects={profile?.subjects ?? []}
        subjectCounts={subjectCounts ?? []}
        activeConversationId={conversationId}
      />

      {/* Center — chat canvas */}
      <div className="relative flex flex-1 flex-col overflow-hidden bg-background">
        <div className="aurora" aria-hidden />

        {/* Header */}
        <div className="relative z-10 flex h-14 items-center gap-2.5 border-b border-border/60 px-5">
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
              {streaming &&
                (streaming.isStreaming && !streaming.content ? (
                  <TypingIndicator />
                ) : (
                  <>
                    <StreamingMessage
                      content={streaming.content}
                      isStreaming={streaming.isStreaming}
                    />
                    {streamingImage && (
                      <div className="mx-auto w-full max-w-3xl pl-10">
                        <AttachmentImage attachment={streamingImage} />
                      </div>
                    )}
                  </>
                ))}
              <div ref={bottomRef} />
            </div>
          )}
        </ScrollArea>

        <div className="relative z-10 px-4 pb-4 pt-2">
          <div className="mx-auto max-w-3xl">
            <ChatInput onSend={sendMessage} disabled={isStreaming} />
            <p className="mt-2 text-center text-[11px] text-muted-foreground/70">
              Roognis may make mistakes. Verify important information.
            </p>
          </div>
        </div>
      </div>

      <ContextPanel profile={profile} analytics={analytics} />
    </div>
  )
}
