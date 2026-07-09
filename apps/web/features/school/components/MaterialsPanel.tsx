'use client'

import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Loader2,
  Sparkles,
  Trash2,
  Upload,
} from 'lucide-react'
import { schoolApi, type Material } from '@/lib/api/school'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

const POLL_MS = 3000

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function StatusPill({ status }: { status: Material['status'] }) {
  const map = {
    ready: { icon: CheckCircle2, cls: 'text-emerald-600 bg-emerald-50', label: 'Ready' },
    processing: { icon: Loader2, cls: 'text-amber-600 bg-amber-50', label: 'Processing' },
    pending: { icon: Loader2, cls: 'text-amber-600 bg-amber-50', label: 'Queued' },
    failed: { icon: AlertCircle, cls: 'text-red-600 bg-red-50', label: 'Failed' },
  } as const
  const { icon: Icon, cls, label } = map[status]
  return (
    <span
      className={cn(
        'flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium',
        cls
      )}
    >
      <Icon className={cn('h-3 w-3', status !== 'ready' && status !== 'failed' && 'animate-spin')} />
      {label}
    </span>
  )
}

export function MaterialsPanel({ classroomId }: { classroomId: string }) {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [chapter, setChapter] = useState('')
  const [dragging, setDragging] = useState(false)

  const { data: materials = [] } = useQuery({
    queryKey: ['school', 'materials', classroomId],
    queryFn: () => schoolApi.getMaterials(classroomId),
    select: (r) => r.data,
    // Keep polling while anything is still ingesting so the status pills update.
    refetchInterval: (q) =>
      (q.state.data?.data ?? []).some(
        (m: Material) => m.status === 'processing' || m.status === 'pending'
      )
        ? POLL_MS
        : false,
  })

  const invalidate = () =>
    qc.invalidateQueries({ queryKey: ['school', 'materials', classroomId] })

  const upload = useMutation({
    mutationFn: (file: File) =>
      schoolApi.uploadMaterial(classroomId, file, chapter.trim() || undefined),
    onSuccess: () => {
      toast.success('Material uploaded — grounding the tutor…')
      setChapter('')
      qc.invalidateQueries({ queryKey: ['school', 'classroom', classroomId] })
      invalidate()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const remove = useMutation({
    mutationFn: (id: string) => schoolApi.deleteMaterial(classroomId, id),
    onSuccess: () => {
      toast.success('Material removed')
      invalidate()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const onFiles = (files: FileList | null) => {
    if (!files?.length) return
    Array.from(files).forEach((f) => upload.mutate(f))
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Explainer — why uploading here matters */}
      <div className="flex items-start gap-2 rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm">
        <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        <p className="text-muted-foreground">
          Files you add here become your class&apos;s knowledge base. Your students&apos;
          AI tutor answers straight from <span className="font-medium text-foreground">your material</span> —
          textbook chapters, notes, worksheets.
        </p>
      </div>

      {/* Dropzone */}
      <Card>
        <CardContent className="flex flex-col gap-3 p-4">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto]">
            <Input
              placeholder="Chapter or topic (optional) — e.g. Fractions"
              value={chapter}
              onChange={(e) => setChapter(e.target.value)}
            />
            <Button
              className="gap-1"
              disabled={upload.isPending}
              onClick={() => fileRef.current?.click()}
            >
              {upload.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              Upload files
            </Button>
          </div>

          <div
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragging(false)
              onFiles(e.dataTransfer.files)
            }}
            onClick={() => fileRef.current?.click()}
            className={cn(
              'flex cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed py-8 text-center transition-colors',
              dragging
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-primary/40'
            )}
          >
            <Upload className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm font-medium">Drop files here or click to browse</p>
            <p className="text-xs text-muted-foreground">PDF, DOCX, TXT, Markdown</p>
          </div>
          <input
            ref={fileRef}
            type="file"
            multiple
            className="hidden"
            accept=".pdf,.docx,.txt,.md"
            onChange={(e) => {
              onFiles(e.target.files)
              e.target.value = ''
            }}
          />
        </CardContent>
      </Card>

      {/* Materials list */}
      {materials.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
            <FileText className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No materials yet. Upload a chapter to ground your students&apos; tutor.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-2">
          {materials.map((m) => (
            <Card key={m.id}>
              <CardContent className="flex items-center gap-3 p-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <FileText className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-medium">{m.title || m.filename}</span>
                    <StatusPill status={m.status} />
                  </div>
                  <div className="truncate text-xs text-muted-foreground">
                    {m.chapter ? `${m.chapter} · ` : ''}
                    {formatBytes(m.file_size)}
                    {m.status === 'ready' ? ` · ${m.chunk_count} passages` : ''}
                    {m.status === 'failed' && m.error_message ? ` · ${m.error_message}` : ''}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-destructive"
                  onClick={() => remove.mutate(m.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
