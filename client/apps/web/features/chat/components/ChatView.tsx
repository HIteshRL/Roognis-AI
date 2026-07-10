'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { PenSquare } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { chatApi } from '@/lib/api/chat'
import { useChatStore } from '@/lib/stores/chat.store'
import { useChat } from '../hooks/useChat'
import { ChatInput } from './ChatInput'
import { MessageBubble } from './MessageBubble'
import { ConversationList } from './ConversationList'
import { StreamingMessage } from './StreamingMessage'
import { TypingIndicator } from './TypingIndicator'

interface ChatViewProps {
  conversationId?: string
}

export function ChatView({ conversationId }: ChatViewProps) {
  const setConversations = useChatStore((s) => s.setConversations)

  const { data: historyData } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => chatApi.listConversations(),
    select: (r) => r.data,
  })

  useEffect(() => {
    if (historyData) setConversations(historyData as any)
  }, [historyData, setConversations])

  const searchParams = useSearchParams()
  const chapterId = searchParams.get('chapter') ?? undefined
  const chapterTitle = searchParams.get('title') ?? undefined

  const { messages, streaming, sendMessage, bottomRef } = useChat(conversationId, chapterId)
  const conversations = useChatStore((s) => s.conversations)
  const isStreaming = streaming?.isStreaming ?? false

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left panel — conversation list */}
      <aside className="flex h-full w-[220px] flex-col border-r border-border bg-sidebar">
        <div className="flex h-12 items-center justify-between px-3">
          <span className="text-sm font-medium">Conversations</span>
          <Link
            href="/chat"
            className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
            aria-label="New conversation"
          >
            <PenSquare className="h-4 w-4" />
          </Link>
        </div>
        <Separator />
        <ScrollArea className="flex-1 py-2">
          <ConversationList conversations={conversations} />
        </ScrollArea>
      </aside>

      {/* Chat window */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {chapterId && (
          <div className="flex items-center gap-2 border-b bg-primary/5 px-4 py-2 text-sm">
            <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
              Chapter
            </span>
            <span className="text-muted-foreground">
              Answers are scoped to{' '}
              <span className="font-medium text-foreground">{chapterTitle ?? 'this chapter'}</span>
            </span>
          </div>
        )}
        <ScrollArea className="flex-1 p-4">
          {messages.length === 0 && !streaming ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
              <p className="text-lg font-medium">What would you like to learn today?</p>
              <p className="text-sm text-muted-foreground">
                Ask anything — Roognis will help you understand it.
              </p>
            </div>
          ) : (
            <div className="mx-auto flex max-w-3xl flex-col gap-4 pb-4">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {streaming && (
                streaming.isStreaming && !streaming.content ? (
                  <TypingIndicator />
                ) : (
                  <StreamingMessage content={streaming.content} isStreaming={streaming.isStreaming} />
                )
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </ScrollArea>

        {/* Input */}
        <div className="border-t border-border p-4">
          <div className="mx-auto max-w-3xl">
            <ChatInput onSend={sendMessage} disabled={isStreaming} />
            <p className="mt-2 text-center text-xs text-muted-foreground">
              Roognis may make mistakes. Verify important information.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
