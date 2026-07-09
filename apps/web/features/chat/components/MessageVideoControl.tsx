'use client'

import { AlertCircle, Clapperboard, RotateCcw } from 'lucide-react'
import { useVideoJob } from '../hooks/useVideoJob'
import { VideoAttachment } from './VideoAttachment'
import { VideoJobCard } from './VideoJobCard'

interface MessageVideoControlProps {
  messageId: string
}

/**
 * "I don't understand — show me a video" affordance on an assistant message.
 * Renders the generate button, live progress, then the inline player.
 */
export function MessageVideoControl({ messageId }: MessageVideoControlProps) {
  const { start, isStarting, job, isActive } = useVideoJob(messageId)

  if (job?.status === 'completed' && job.attachment_id) {
    return (
      <div className="mt-2">
        <VideoAttachment attachmentId={job.attachment_id} />
      </div>
    )
  }

  if (isStarting || isActive) {
    return <VideoJobCard job={job} isStarting={isStarting} />
  }

  if (job?.status === 'failed') {
    return (
      <div className="mt-2 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-2 text-xs text-red-700">
        <AlertCircle className="h-4 w-4 shrink-0" />
        <span className="flex-1">Video generation failed.</span>
        <button
          onClick={start}
          className="flex items-center gap-1 rounded-md px-2 py-1 font-medium hover:bg-red-100"
        >
          <RotateCcw className="h-3 w-3" />
          Retry
        </button>
      </div>
    )
  }

  return (
    <button
      onClick={start}
      className="mt-2 flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
    >
      <Clapperboard className="h-3.5 w-3.5" />
      I don&apos;t understand — show me a video
    </button>
  )
}
