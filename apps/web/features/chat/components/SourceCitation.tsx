'use client'

import { BookOpen, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import type { StreamSourceDto } from '@roognis/shared'

interface SourceCitationProps {
  sources: StreamSourceDto[]
  cascadeLevel: string
}

const levelLabels: Record<string, string> = {
  exact: 'Matched chapter',
  subject: 'Matched subject',
  grade: 'Matched grade',
  unscoped: 'General search',
  none: '',
}

export function SourceCitation({ sources, cascadeLevel }: SourceCitationProps) {
  const [expanded, setExpanded] = useState(false)

  if (sources.length === 0) return null

  const label = levelLabels[cascadeLevel] ?? cascadeLevel

  return (
    <div className="ml-10 mt-1">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        <BookOpen className="h-3 w-3" />
        <span>
          {sources.length} source{sources.length !== 1 ? 's' : ''}
        </span>
        {label && (
          <Badge variant="outline" className="px-1.5 py-0 text-[10px]">
            {label}
          </Badge>
        )}
        {expanded ? (
          <ChevronUp className="h-3 w-3" />
        ) : (
          <ChevronDown className="h-3 w-3" />
        )}
      </button>

      {expanded && (
        <ul className="mt-1.5 space-y-1 border-l-2 border-border pl-3">
          {sources.map((src, i) => (
            <li key={i} className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground">
                {src.title ?? 'Untitled'}
              </span>
              {src.subject && (
                <span className="ml-1.5 text-muted-foreground">
                  {src.subject}
                  {src.chapter ? ` > ${src.chapter}` : ''}
                </span>
              )}
              <span className="ml-1.5 tabular-nums opacity-60">
                {Math.round(src.score * 100)}%
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
