'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ArrowLeft, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { chatApi } from '@/lib/api/chat'
import { useChatStore } from '@/lib/stores/chat.store'
import { Badge } from '@/components/ui/badge'
import type { ConversationDto } from '@roognis/shared'

interface ConversationListProps {
  conversations: ConversationDto[]
  subjectLabel: string | null
  onBack: () => void
}

export function ConversationList({ conversations, subjectLabel, onBack }: ConversationListProps) {
  const pathname = usePathname()
  const removeConversation = useChatStore((s) => s.removeConversation)

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.preventDefault()
    e.stopPropagation()
    try {
      await chatApi.deleteConversation(id)
      removeConversation(id)
      toast.success('Conversation deleted')
    } catch {
      toast.error('Could not delete conversation')
    }
  }

  return (
    <div>
      {/* Back header when viewing a subject */}
      {subjectLabel !== null && (
        <button
          onClick={onBack}
          className="flex w-full items-center gap-2 px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-3 w-3" />
          <span className="truncate">{subjectLabel || 'All'}</span>
        </button>
      )}

      {conversations.length === 0 ? (
        <p className="px-3 py-4 text-xs text-muted-foreground">No conversations yet.</p>
      ) : (
        <ul className="space-y-0.5 px-2">
          {conversations.map((conv) => {
            const isActive = pathname === `/chat/${conv.id}`
            return (
              <li key={conv.id}>
                <Link
                  href={`/chat/${conv.id}`}
                  className={cn(
                    'group flex items-center justify-between rounded-md px-3 py-2 text-sm transition-colors',
                    isActive
                      ? 'bg-accent text-accent-foreground'
                      : 'text-sidebar-foreground/70 hover:bg-accent/50 hover:text-sidebar-foreground'
                  )}
                >
                  <div className="flex min-w-0 flex-col gap-0.5">
                    <span className="truncate">{conv.title ?? 'New conversation'}</span>
                    {conv.chapter && (
                      <Badge variant="secondary" className="w-fit text-[10px] px-1.5 py-0">
                        {conv.chapter}
                      </Badge>
                    )}
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, conv.id)}
                    className="ml-2 shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100"
                    aria-label="Delete conversation"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
