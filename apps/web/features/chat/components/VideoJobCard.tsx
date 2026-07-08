'use client'

import { Film, Loader2 } from 'lucide-react'
import type { MediaJobDto } from '@roognis/shared'

interface VideoJobCardProps {
  job: MediaJobDto | null
  isStarting: boolean
}

export function VideoJobCard({ job, isStarting }: VideoJobCardProps) {
  const status = isStarting ? 'queued' : (job?.status ?? 'queued')
  const label =
    status === 'running'
      ? 'Generating your explainer video…'
      : status === 'queued'
        ? 'Queued for video generation…'
        : 'Preparing…'
  const progress = job?.progress ?? 5

  return (
    <div className="mt-2 w-full max-w-md rounded-lg border border-border bg-muted/40 p-3">
      <div className="flex items-center gap-2 text-sm">
        <Film className="h-4 w-4 text-primary" />
        <span className="font-medium">Video</span>
        <Loader2 className="ml-auto h-4 w-4 animate-spin text-muted-foreground" />
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{label}</p>
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all duration-500"
          style={{ width: `${Math.max(5, progress)}%` }}
        />
      </div>
      <p className="mt-1 text-[10px] text-muted-foreground">
        This can take a while — video is generated on the GPU.
      </p>
    </div>
  )
}
