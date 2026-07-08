'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { Avatar } from './MessageBubble'

interface StreamingMessageProps {
  content: string
  isStreaming: boolean
}

export function StreamingMessage({ content, isStreaming }: StreamingMessageProps) {
  return (
    <div className="flex gap-3">
      <Avatar isUser={false} />
      <div className="flex min-w-0 max-w-[80%] flex-col gap-1">
        <span className="px-1 text-[11px] font-medium text-muted-foreground">Roognis</span>
        <div className="rounded-2xl rounded-tl-md bg-card/70 px-4 py-3 text-sm text-foreground shadow-sm ring-1 ring-border backdrop-blur">
          <div className="chat-prose prose prose-sm dark:prose-invert max-w-none leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {content}
            </ReactMarkdown>
          </div>
          {isStreaming && <span className="stream-caret" aria-label="Roognis is typing" />}
        </div>
      </div>
    </div>
  )
}
