'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { BookText, ChevronDown, ChevronRight, MessageSquarePlus, Plus } from 'lucide-react'
import { chatApi } from '@/lib/api/chat'
import { useChatStore } from '@/lib/stores/chat.store'
import { cn } from '@/lib/utils'
import type { ConversationDto, SubjectCountDto } from '@roognis/shared'

interface SubjectChapterRailProps {
  subjects: string[]
  subjectCounts: SubjectCountDto[]
  activeConversationId?: string
}

const SUBJECT_ACCENTS = [
  'bg-blue-500',
  'bg-emerald-500',
  'bg-violet-500',
  'bg-amber-500',
  'bg-rose-500',
  'bg-cyan-500',
]

export function SubjectChapterRail({
  subjects,
  subjectCounts,
  activeConversationId,
}: SubjectChapterRailProps) {
  const router = useRouter()
  const setPendingChat = useChatStore((s) => s.setPendingChat)
  const [expanded, setExpanded] = useState<string | null>(null)

  const countFor = (subject: string) =>
    subjectCounts.find((c) => c.subject === subject)?.count ?? 0

  const startNewChat = (subject: string | null, chapter: string | null) => {
    setPendingChat(subject, chapter)
    router.push('/chat')
  }

  const allSubjects =
    subjects.length > 0
      ? subjects
      : subjectCounts.map((c) => c.subject).filter((s) => s !== 'General')

  return (
    <aside className="flex h-full w-72 flex-col border-r border-border bg-sidebar">
      <div className="flex h-14 items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <BookText className="h-5 w-5 text-primary" />
          <span className="font-semibold tracking-tight">Classroom</span>
        </div>
        <button
          onClick={() => startNewChat(null, null)}
          className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
          aria-label="New chat"
        >
          <MessageSquarePlus className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {allSubjects.length === 0 ? (
          <p className="px-3 py-6 text-center text-xs text-muted-foreground">
            No subjects yet. Start a new chat to begin.
          </p>
        ) : (
          allSubjects.map((subject, i) => (
            <SubjectItem
              key={subject}
              subject={subject}
              accent={SUBJECT_ACCENTS[i % SUBJECT_ACCENTS.length]}
              count={countFor(subject)}
              isExpanded={expanded === subject}
              onToggle={() => setExpanded(expanded === subject ? null : subject)}
              onNewChapterChat={(chapter) => startNewChat(subject, chapter)}
              onOpenConversation={(id) => router.push(`/chat/${id}`)}
              activeConversationId={activeConversationId}
            />
          ))
        )}
      </div>
    </aside>
  )
}

interface SubjectItemProps {
  subject: string
  accent: string
  count: number
  isExpanded: boolean
  onToggle: () => void
  onNewChapterChat: (chapter: string | null) => void
  onOpenConversation: (id: string) => void
  activeConversationId?: string
}

function SubjectItem({
  subject,
  accent,
  count,
  isExpanded,
  onToggle,
  onNewChapterChat,
  onOpenConversation,
  activeConversationId,
}: SubjectItemProps) {
  const { data: chapters } = useQuery({
    queryKey: ['chat-chapters', subject],
    queryFn: () => chatApi.getChapters(subject),
    select: (r) => r.data,
    enabled: isExpanded,
  })

  const { data: conversationsData } = useQuery({
    queryKey: ['conversations', 'rail', subject],
    queryFn: () => chatApi.listConversations(1, 30, subject),
    select: (r) => r.data as unknown as ConversationDto[],
    enabled: isExpanded,
  })

  const conversations = conversationsData ?? []

  return (
    <div className="mb-1">
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm font-medium hover:bg-accent/60"
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
        <span className={cn('h-2.5 w-2.5 rounded-full', accent)} />
        <span className="flex-1 truncate text-left">{subject}</span>
        <span className="text-xs text-muted-foreground">{count}</span>
      </button>

      {isExpanded && (
        <div className="ml-4 mt-1 space-y-2 border-l border-border pl-3">
          <div>
            <div className="mb-1 flex items-center justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Chapters
              </span>
              <button
                onClick={() => onNewChapterChat(null)}
                className="flex items-center gap-1 text-[10px] text-primary hover:underline"
              >
                <Plus className="h-3 w-3" />
                New
              </button>
            </div>
            <div className="flex flex-wrap gap-1">
              {(chapters ?? []).length === 0 ? (
                <span className="text-[11px] text-muted-foreground">No chapters yet</span>
              ) : (
                (chapters ?? []).map((ch) => (
                  <button
                    key={ch.chapter}
                    onClick={() => onNewChapterChat(ch.chapter)}
                    className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground hover:border-primary/50 hover:text-foreground"
                  >
                    {ch.chapter}
                  </button>
                ))
              )}
            </div>
          </div>

          <div>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Inferences
            </span>
            <div className="mt-1 space-y-0.5">
              {conversations.length === 0 ? (
                <span className="text-[11px] text-muted-foreground">No conversations</span>
              ) : (
                conversations.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => onOpenConversation(conv.id)}
                    className={cn(
                      'block w-full truncate rounded-md px-2 py-1 text-left text-xs hover:bg-accent/60',
                      conv.id === activeConversationId
                        ? 'bg-accent font-medium text-accent-foreground'
                        : 'text-muted-foreground',
                    )}
                  >
                    {conv.title || 'Untitled'}
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
