'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { BookOpen, Plus, Trash2, Loader2, FileText } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { knowledgeApi } from '@/lib/api/knowledge'

export function KnowledgeLibraryView() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [institution, setInstitution] = useState('')
  const [subject, setSubject] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['knowledge-bases'],
    queryFn: () => knowledgeApi.listKnowledgeBases(),
    select: (r) => r.data,
  })

  const createMutation = useMutation({
    mutationFn: () => knowledgeApi.createKnowledgeBase({ name, institution, subject }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['knowledge-bases'] })
      toast.success('Knowledge base created')
      setShowForm(false)
      setName('')
    },
    onError: () => toast.error('Failed to create knowledge base'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => knowledgeApi.deleteKnowledgeBase(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['knowledge-bases'] })
      toast.success('Knowledge base deleted')
    },
    onError: () => toast.error('Failed to delete knowledge base'),
  })

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Knowledge Library</h1>
        <Button size="sm" onClick={() => setShowForm((v) => !v)}>
          <Plus className="h-4 w-4" />
          New knowledge base
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Create knowledge base</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1">
              <Label>Name *</Label>
              <Input
                placeholder="e.g. Computer Science Year 1"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label>Institution</Label>
                <Input placeholder="e.g. MIT" value={institution} onChange={(e) => setInstitution(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label>Subject</Label>
                <Input placeholder="e.g. Algorithms" value={subject} onChange={(e) => setSubject(e.target.value)} />
              </div>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => createMutation.mutate()} disabled={!name || createMutation.isPending}>
                {createMutation.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                Create
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : !data?.length ? (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <BookOpen className="h-10 w-10 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">No knowledge bases yet. Create one to start uploading documents.</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((kb) => (
            <Card key={kb.id} className="group">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base leading-tight">{kb.name}</CardTitle>
                  <button
                    onClick={() => deleteMutation.mutate(kb.id)}
                    className="shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100"
                    aria-label="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                <div className="flex flex-wrap gap-1">
                  {kb.institution && <Badge variant="outline" className="text-xs">{kb.institution}</Badge>}
                  {kb.subject && <Badge variant="secondary" className="text-xs">{kb.subject}</Badge>}
                </div>
              </CardHeader>
              <CardContent className="flex items-center justify-between">
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <FileText className="h-3 w-3" />
                  {kb.document_count} document{kb.document_count !== 1 ? 's' : ''}
                </span>
                <Button size="sm" variant="ghost" asChild>
                  <Link href={`/admin/upload?kb=${kb.id}`}>Upload docs →</Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
