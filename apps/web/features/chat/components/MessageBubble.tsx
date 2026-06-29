'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import rehypeSanitize from 'rehype-sanitize'
import { Check, Copy } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { MessageDto } from '@roognis/shared'

interface MessageBubbleProps {
  message: MessageDto
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn('group flex gap-3', isUser && 'flex-row-reverse')}>
      {/* Avatar indicator */}
      <div
        className={cn(
          'mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-medium',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
        )}
      >
        {isUser ? 'Y' : 'R'}
      </div>

      {/* Bubble */}
      <div
        className={cn(
          'relative max-w-[75%] rounded-2xl px-4 py-3',
          isUser
            ? 'rounded-tr-sm bg-primary text-primary-foreground'
            : 'rounded-tl-sm bg-muted text-foreground'
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeSanitize, rehypeHighlight]}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Copy button */}
        <button
          onClick={handleCopy}
          className={cn(
            'absolute -top-2 right-2 rounded-md border border-border bg-background p-1 text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover:opacity-100',
            copied && 'opacity-100 text-green-500'
          )}
          aria-label="Copy message"
        >
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
        </button>
      </div>
    </div>
  )
}
