'use client'

import { useEffect, useState } from 'react'
import { Loader2, VideoOff } from 'lucide-react'
import { chatApi } from '@/lib/api/chat'

interface VideoAttachmentProps {
  attachmentId: string
}

export function VideoAttachment({ attachmentId }: VideoAttachmentProps) {
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    let objectUrl: string | null = null

    chatApi
      .fetchAttachmentUrl(attachmentId)
      .then((blobUrl) => {
        if (!active) {
          URL.revokeObjectURL(blobUrl)
          return
        }
        objectUrl = blobUrl
        setUrl(blobUrl)
      })
      .catch(() => {
        if (active) setFailed(true)
      })

    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [attachmentId])

  if (failed) {
    return (
      <div className="flex h-40 w-full max-w-md items-center justify-center rounded-lg border border-border bg-muted text-muted-foreground">
        <VideoOff className="h-6 w-6" />
      </div>
    )
  }

  if (!url) {
    return (
      <div className="flex h-40 w-full max-w-md items-center justify-center rounded-lg border border-border bg-muted">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <video
      src={url}
      controls
      className="max-h-72 w-full max-w-md rounded-lg border border-border bg-black"
    />
  )
}
