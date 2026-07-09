'use client'

import { BookOpen, ChevronRight, Inbox, MessageSquare } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SubjectCountDto } from '@roognis/shared'

interface SubjectListProps {
  subjects: string[]
  subjectCounts: SubjectCountDto[]
  selectedSubject: string | null
  onSelect: (subject: string | null) => void
}

export function SubjectList({ subjects, subjectCounts, selectedSubject, onSelect }: SubjectListProps) {
  const countMap = new Map(subjectCounts.map((s) => [s.subject, s.count]))
  const generalCount = countMap.get('General') ?? 0

  const allSubjects = Array.from(new Set([...subjects, ...subjectCounts.map((s) => s.subject)]))
    .filter((s) => s !== 'General')
    .sort()

  const totalCount = subjectCounts.reduce((sum, s) => sum + s.count, 0)

  return (
    <ul className="space-y-0.5 px-2">
      {/* All conversations */}
      <li>
        <button
          onClick={() => onSelect(null)}
          className={cn(
            'flex w-full items-center justify-between rounded-md px-3 py-2 text-sm transition-colors',
            selectedSubject === null
              ? 'bg-accent text-accent-foreground'
              : 'text-sidebar-foreground/70 hover:bg-accent/50 hover:text-sidebar-foreground'
          )}
        >
          <span className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 shrink-0" />
            <span>All Conversations</span>
          </span>
          {totalCount > 0 && (
            <span className="text-xs text-muted-foreground">{totalCount}</span>
          )}
        </button>
      </li>

      {/* Per-subject items */}
      {allSubjects.map((subject) => {
        const count = countMap.get(subject) ?? 0
        return (
          <li key={subject}>
            <button
              onClick={() => onSelect(subject)}
              className={cn(
                'flex w-full items-center justify-between rounded-md px-3 py-2 text-sm transition-colors',
                selectedSubject === subject
                  ? 'bg-accent text-accent-foreground'
                  : 'text-sidebar-foreground/70 hover:bg-accent/50 hover:text-sidebar-foreground'
              )}
            >
              <span className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 shrink-0" />
                <span className="truncate">{subject}</span>
              </span>
              <span className="flex items-center gap-1">
                {count > 0 && (
                  <span className="text-xs text-muted-foreground">{count}</span>
                )}
                <ChevronRight className="h-3 w-3 text-muted-foreground" />
              </span>
            </button>
          </li>
        )
      })}

      {/* General (no subject) */}
      {generalCount > 0 && (
        <li>
          <button
            onClick={() => onSelect('General')}
            className={cn(
              'flex w-full items-center justify-between rounded-md px-3 py-2 text-sm transition-colors',
              selectedSubject === 'General'
                ? 'bg-accent text-accent-foreground'
                : 'text-sidebar-foreground/70 hover:bg-accent/50 hover:text-sidebar-foreground'
            )}
          >
            <span className="flex items-center gap-2">
              <Inbox className="h-4 w-4 shrink-0" />
              <span>General</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="text-xs text-muted-foreground">{generalCount}</span>
              <ChevronRight className="h-3 w-3 text-muted-foreground" />
            </span>
          </button>
        </li>
      )}

      {allSubjects.length === 0 && generalCount === 0 && (
        <li className="px-3 py-4 text-xs text-muted-foreground">
          No subjects configured. Update your profile to add subjects.
        </li>
      )}
    </ul>
  )
}
