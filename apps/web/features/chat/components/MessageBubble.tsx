'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import rehypeSanitize from 'rehype-sanitize'
import { Check, Copy, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { MessageDto } from '@roognis/shared'
import { AttachmentImage } from './AttachmentImage'
import { VideoAttachment } from './VideoAttachment'
import { MessageVideoControl } from './MessageVideoControl'

interface MessageBubbleProps {
  message: MessageDto
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'
  const attachments = message.attachments ?? []
  const imageAttachments = attachments.filter((a) => a.kind === 'image')
  const videoAttachments = attachments.filter((a) => a.kind === 'video')

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn('msg-in group flex gap-3', isUser && 'flex-row-reverse')}>
      <Avatar isUser={isUser} />

      <div className={cn('flex min-w-0 max-w-[80%] flex-col gap-1', isUser && 'items-end')}>
        <span className="px-1 text-[11px] font-medium text-muted-foreground">
          {isUser ? 'You' : 'Roognis'}
        </span>

        <div
          className={cn(
            'relative rounded-2xl px-4 py-3 text-sm shadow-sm ring-1',
            isUser
              ? 'rounded-tr-md bg-gradient-to-br from-primary to-violet-500 text-primary-foreground ring-primary/20'
              : 'rounded-tl-md bg-card/70 text-foreground ring-border backdrop-blur'
          )}
        >
          {imageAttachments.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-2">
              {imageAttachments.map((att) => (
                <AttachmentImage
                  key={att.id}
                  attachment={att}
                  alt={
                    isAssistant
                      ? 'AI-generated illustration for this explanation'
                      : 'Image you attached to your question'
                  }
                />
              ))}
            </div>
          )}

          {isUser ? (
            <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
          ) : (
            <div className="chat-prose prose prose-sm dark:prose-invert max-w-none leading-relaxed">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeSanitize, rehypeHighlight]}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}

          {videoAttachments.map((att) => (
            <div key={att.id} className="mt-2">
              <VideoAttachment attachmentId={att.id} />
            </div>
          ))}

          {isAssistant && videoAttachments.length === 0 && (
            <MessageVideoControl messageId={message.id} />
          )}

          <button
            onClick={handleCopy}
            className={cn(
              'absolute -bottom-3 rounded-lg border border-border bg-background/90 p-1.5 text-muted-foreground opacity-0 shadow-sm backdrop-blur transition-all hover:text-foreground group-hover:opacity-100',
              isUser ? 'left-2' : 'right-2',
              copied && 'text-emerald-500 opacity-100'
            )}
            aria-label="Copy message"
          >
            {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
          </button>
        </div>
      </div>
    </div>
  )
}

export function Avatar({ isUser }: { isUser: boolean }) {
  if (isUser) {
    return (
      <div className="mt-6 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-muted text-xs font-semibold text-muted-foreground ring-1 ring-border">
        You
      </div>
    )
  }
  return (
    <div className="mt-6 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-sky-500 shadow-md shadow-primary/30 ring-1 ring-primary/30">
      <Sparkles className="h-4 w-4 text-white" />
    </div>
  )
}
