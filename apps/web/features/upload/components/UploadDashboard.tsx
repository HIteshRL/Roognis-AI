'use client'

import { useCallback, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { useDropzone } from 'react-dropzone'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { CheckCircle2, FileText, Loader2, Upload, XCircle } from 'lucide-react'
import { useAuthStore } from '@/lib/stores/auth.store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { knowledgeApi, type Document } from '@/lib/api/knowledge'

const STATUS_COLORS = {
  pending: 'warning',
  processing: 'warning',
  ready: 'success',
  failed: 'destructive',
} as const

export function UploadDashboard() {
  const searchParams = useSearchParams()
  const kbId = searchParams.get('kb') ?? ''
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  const [uploading, setUploading] = useState(false)

  const { data: kbs } = useQuery({
    queryKey: ['knowledge-bases'],
    queryFn: () => knowledgeApi.listKnowledgeBases(),
    select: (r) => r.data,
  })

  const [selectedKb, setSelectedKb] = useState(kbId)
  const activeKb = kbs?.find((k) => k.id === selectedKb)

  const { data: docs, isLoading: docsLoading } = useQuery({
    queryKey: ['documents', selectedKb],
    queryFn: () => knowledgeApi.listDocuments(selectedKb),
    select: (r) => r.data,
    enabled: !!selectedKb,
    refetchInterval: (query) => {
      const docs = query.state.data?.data
      const hasProcessing = docs?.some((d) => d.status === 'processing' || d.status === 'pending')
      return hasProcessing ? 3000 : false
    },
  })

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (!selectedKb) { toast.error('Select a knowledge base first'); return }
      setUploading(true)
      for (const file of acceptedFiles) {
        try {
          await knowledgeApi.uploadDocument(selectedKb, file, token ?? '')
          toast.success(`Uploaded: ${file.name}`)
          qc.invalidateQueries({ queryKey: ['documents', selectedKb] })
        } catch (e: any) {
          toast.error(`Failed: ${file.name} — ${e.message}`)
        }
      }
      setUploading(false)
    },
    [selectedKb, token, qc]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'text/html': ['.html'],
    },
  })

  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="text-xl font-semibold">Upload Documents</h1>

      {/* KB selector */}
      <Card>
        <CardHeader><CardTitle className="text-base">Select knowledge base</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {kbs?.map((kb) => (
              <button
                key={kb.id}
                onClick={() => setSelectedKb(kb.id)}
                className={`rounded-full border px-3 py-1 text-sm transition-colors ${
                  selectedKb === kb.id
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-border hover:bg-accent'
                }`}
              >
                {kb.name}
              </button>
            ))}
            {!kbs?.length && (
              <p className="text-sm text-muted-foreground">
                No knowledge bases yet. Create one in the Library first.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Drop zone */}
      {selectedKb && (
        <div
          {...getRootProps()}
          className={`flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-12 text-center transition-colors ${
            isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
          } ${uploading ? 'pointer-events-none opacity-50' : 'cursor-pointer'}`}
        >
          <input {...getInputProps()} />
          {uploading ? (
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          ) : (
            <Upload className="h-8 w-8 text-muted-foreground" />
          )}
          <div>
            <p className="font-medium">
              {isDragActive ? 'Drop files here' : 'Drag & drop or click to upload'}
            </p>
            <p className="text-xs text-muted-foreground">PDF, DOCX, PPTX, TXT, MD, HTML — max 50 MB</p>
          </div>
        </div>
      )}

      {/* Document list */}
      {selectedKb && (
        <div className="flex flex-col gap-2">
          <h2 className="text-sm font-medium">
            Documents in{' '}
            <span className="text-primary">{activeKb?.name ?? selectedKb}</span>
          </h2>
          {docsLoading ? (
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          ) : !docs?.length ? (
            <p className="text-sm text-muted-foreground">No documents yet.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {docs.map((doc) => (
                <DocumentRow key={doc.id} doc={doc} kbId={selectedKb} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function DocumentRow({ doc, kbId }: { doc: Document; kbId: string }) {
  const qc = useQueryClient()

  const handleDelete = async () => {
    try {
      await knowledgeApi.deleteDocument(kbId, doc.id)
      qc.invalidateQueries({ queryKey: ['documents', kbId] })
      toast.success('Document deleted')
    } catch {
      toast.error('Failed to delete document')
    }
  }

  return (
    <div className="flex items-center gap-3 rounded-lg border border-border px-4 py-3">
      <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
      <div className="flex-1 min-w-0">
        <p className="truncate text-sm font-medium">{doc.filename}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <Badge variant={STATUS_COLORS[doc.status] ?? 'outline'} className="text-xs">
            {doc.status}
          </Badge>
          {doc.status === 'ready' && (
            <span className="text-xs text-muted-foreground">{doc.chunk_count} chunks</span>
          )}
          {(doc.status === 'processing' || doc.status === 'pending') && (
            <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
          )}
        </div>
        {doc.status === 'failed' && doc.error_message && (
          <p className="text-xs text-destructive mt-0.5 truncate">{doc.error_message}</p>
        )}
      </div>
      <button
        onClick={handleDelete}
        className="shrink-0 text-muted-foreground hover:text-destructive"
        aria-label="Delete"
      >
        <XCircle className="h-4 w-4" />
      </button>
    </div>
  )
}
