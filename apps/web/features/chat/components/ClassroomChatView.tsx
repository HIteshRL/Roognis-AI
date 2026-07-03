'use client'

import { useQuery } from '@tanstack/react-query'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { chatApi } from '@/lib/api/chat'
import { studentApi } from '@/lib/api/student'
import { useChatStore } from '@/lib/stores/chat.store'
import type { AttachmentDto } from '@roognis/shared'
import { useChat } from '../hooks/useChat'
import { AttachmentImage } from './AttachmentImage'
import { ChatInput } from './ChatInput'
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
      <div className="flex flex-1 flex-col overflow-hidden">
        {currentSubject && (
          <div className="flex items-center gap-2 border-b border-border px-4 py-2">
            <Badge variant="secondary" className="text-xs">
              {currentSubject}
            </Badge>
            {currentChapter && (
              <Badge variant="outline" className="text-xs">
                {currentChapter}
              </Badge>
            )}
          </div>
        )}

        <ScrollArea className="flex-1 p-4">
          {messages.length === 0 && !streaming ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
              <p className="text-lg font-medium">
                {currentSubject
                  ? `Ask anything about ${currentSubject}`
                  : 'What would you like to learn today?'}
              </p>
              <p className="max-w-md text-sm text-muted-foreground">
                Answers come with an illustration. If something is still unclear,
                ask for a video and Roognis will generate one.
              </p>
            </div>
          ) : (
            <div className="mx-auto flex max-w-3xl flex-col gap-4 pb-4">
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

        <div className="border-t border-border p-4">
          <div className="mx-auto max-w-3xl">
            <ChatInput onSend={sendMessage} disabled={isStreaming} />
            <p className="mt-2 text-center text-xs text-muted-foreground">
              Roognis may make mistakes. Verify important information.
            </p>
          </div>
        </div>
      </div>

      <ContextPanel profile={profile} analytics={analytics} />
    </div>
  )
}
