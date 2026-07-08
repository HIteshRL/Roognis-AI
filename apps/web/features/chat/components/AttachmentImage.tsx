'use client'

import { useEffect, useState } from 'react'
import { ImageOff, Loader2 } from 'lucide-react'
import { chatApi } from '@/lib/api/chat'
import type { AttachmentDto } from '@roognis/shared'

interface AttachmentImageProps {
  attachment: AttachmentDto
  alt?: string
}

export function AttachmentImage({ attachment, alt = 'Attached image' }: AttachmentImageProps) {
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    let objectUrl: string | null = null

    chatApi
      .fetchAttachmentUrl(attachment.id)
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
  }, [attachment.id])

  if (failed) {
    return (
      <div className="flex h-40 w-40 items-center justify-center rounded-lg border border-border bg-muted text-muted-foreground">
        <ImageOff className="h-6 w-6" />
      </div>
    )
  }

  if (!url) {
    return (
      <div className="flex h-40 w-40 items-center justify-center rounded-lg border border-border bg-muted">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <a href={url} target="_blank" rel="noopener noreferrer" className="block">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={url}
        alt={alt}
        className="max-h-64 max-w-full rounded-lg border border-border object-contain"
      />
    </a>
  )
}
