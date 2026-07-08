'use client'

import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { ArrowUp, ImagePlus, Loader2, X } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

interface ChatInputProps {
  onSend: (message: string, files?: File[]) => void
  disabled?: boolean
  maxImages?: number
}

interface PendingImage {
  file: File
  previewUrl: string
}

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
const MAX_SIZE_BYTES = 4 * 1024 * 1024

export function ChatInput({ onSend, disabled, maxImages = 4 }: ChatInputProps) {
  const ref = useRef<HTMLTextAreaElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const [images, setImages] = useState<PendingImage[]>([])

  useEffect(() => {
    return () => {
      images.forEach((img) => URL.revokeObjectURL(img.previewUrl))
    }
    // Revoke only on unmount — previews are cleaned individually on remove/submit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const addFiles = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return
    const incoming = Array.from(fileList)
    const accepted: PendingImage[] = []

    for (const file of incoming) {
      if (!ACCEPTED_TYPES.includes(file.type)) {
        toast.error(`Unsupported image type: ${file.name}`)
        continue
      }
      if (file.size > MAX_SIZE_BYTES) {
        toast.error(`Image too large (max 4MB): ${file.name}`)
        continue
      }
      accepted.push({ file, previewUrl: URL.createObjectURL(file) })
    }

    setImages((prev) => {
      const combined = [...prev, ...accepted]
      if (combined.length > maxImages) {
        toast.error(`You can attach up to ${maxImages} images`)
        combined.slice(maxImages).forEach((img) => URL.revokeObjectURL(img.previewUrl))
      }
      return combined.slice(0, maxImages)
    })
  }

  const removeImage = (index: number) => {
    setImages((prev) => {
      const target = prev[index]
      if (target) URL.revokeObjectURL(target.previewUrl)
      return prev.filter((_, i) => i !== index)
    })
  }

  const submit = () => {
    const value = ref.current?.value.trim() ?? ''
    if ((!value && images.length === 0) || disabled) return

    onSend(value, images.length > 0 ? images.map((img) => img.file) : undefined)

    if (ref.current) {
      ref.current.value = ''
      ref.current.style.height = 'auto'
    }
    setImages([])
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const handleInput = () => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }

  return (
    <div className="flex flex-col gap-2 rounded-[1.4rem] border border-border/70 bg-card/70 px-3 py-2.5 shadow-lg shadow-black/5 backdrop-blur-xl transition-all focus-within:border-primary/40 focus-within:shadow-primary/10 focus-within:ring-2 focus-within:ring-primary/15">
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2 px-1 pt-1">
          {images.map((img, i) => (
            <div key={i} className="relative h-16 w-16 overflow-hidden rounded-xl ring-1 ring-border">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={img.previewUrl} alt={img.file.name} className="h-full w-full object-cover" />
              <button
                onClick={() => removeImage(i)}
                className="absolute right-0.5 top-0.5 rounded-full bg-background/80 p-0.5 text-foreground backdrop-blur hover:bg-background"
                aria-label={`Remove ${img.file.name}`}
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2">
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPTED_TYPES.join(',')}
          multiple
          className="hidden"
          onChange={(e) => {
            addFiles(e.target.files)
            e.target.value = ''
          }}
        />
        <button
          onClick={() => fileRef.current?.click()}
          disabled={disabled}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-40"
          aria-label="Attach image"
        >
          <ImagePlus className="h-[18px] w-[18px]" />
        </button>

        <textarea
          ref={ref}
          rows={1}
          placeholder="Ask Roognis anything…"
          className="flex-1 resize-none bg-transparent py-2 text-sm leading-relaxed outline-none placeholder:text-muted-foreground/70 disabled:opacity-50"
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          disabled={disabled}
          aria-label="Chat input"
        />

        <button
          onClick={submit}
          disabled={disabled}
          className={cn(
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-violet-500 text-primary-foreground shadow-md shadow-primary/25 transition-all hover:brightness-110 active:scale-95 disabled:opacity-40 disabled:shadow-none'
          )}
          aria-label="Send message"
        >
          {disabled ? <Loader2 className="h-[18px] w-[18px] animate-spin" /> : <ArrowUp className="h-[18px] w-[18px]" />}
        </button>
      </div>
    </div>
  )
}
