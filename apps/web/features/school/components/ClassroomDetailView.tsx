'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { toast } from 'sonner'
import {
  ArrowLeft,
  BookOpen,
  Copy,
  Eye,
  EyeOff,
  Plus,
  Trash2,
  Users,
} from 'lucide-react'
import { schoolApi, type CreateSyllabusPayload } from '@/lib/api/school'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'

export function ClassroomDetailView({ classroomId }: { classroomId: string }) {
  const qc = useQueryClient()
  const [item, setItem] = useState<CreateSyllabusPayload>({ subject: '', chapter: '', topic: '' })

  const { data: classroom } = useQuery({
    queryKey: ['school', 'classroom', classroomId],
    queryFn: () => schoolApi.getClassroom(classroomId),
    select: (r) => r.data,
  })

  const { data: roster = [] } = useQuery({
    queryKey: ['school', 'roster', classroomId],
    queryFn: () => schoolApi.getRoster(classroomId),
    select: (r) => r.data,
  })

  const { data: syllabus = [] } = useQuery({
    queryKey: ['school', 'syllabus', classroomId],
    queryFn: () => schoolApi.getSyllabus(classroomId),
    select: (r) => r.data,
  })

  const invalidateSyllabus = () =>
    qc.invalidateQueries({ queryKey: ['school', 'syllabus', classroomId] })

  const addItem = useMutation({
    mutationFn: () =>
      schoolApi.addSyllabusItem(classroomId, {
        ...item,
        subject: item.subject || classroom?.subject || 'General',
        order_index: syllabus.length,
      }),
    onSuccess: () => {
      toast.success('Syllabus item added')
      setItem({ subject: '', chapter: '', topic: '' })
      invalidateSyllabus()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const togglePublish = useMutation({
    mutationFn: (v: { id: string; publish: boolean }) =>
      schoolApi.updateSyllabusItem(v.id, { is_published: v.publish }),
    onSuccess: () => invalidateSyllabus(),
    onError: (e: Error) => toast.error(e.message),
  })

  const removeItem = useMutation({
    mutationFn: (id: string) => schoolApi.deleteSyllabusItem(id),
    onSuccess: () => {
      toast.success('Removed')
      invalidateSyllabus()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const copyCode = () => {
    if (classroom?.join_code) {
      navigator.clipboard.writeText(classroom.join_code)
      toast.success('Join code copied')
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center gap-3">
        <Link href="/teacher">
          <Button variant="ghost" size="sm" className="gap-1">
            <ArrowLeft className="h-4 w-4" /> Back
          </Button>
        </Link>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{classroom?.name ?? '…'}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {classroom?.subject ?? 'General'}
            {classroom?.grade ? ` · Grade ${classroom.grade}` : ''}
          </p>
        </div>
        <button
          onClick={copyCode}
          className="flex items-center gap-2 rounded-md border border-input bg-card px-4 py-2 transition-colors hover:border-primary/50"
        >
          <div className="text-left">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Join code
            </div>
            <div className="font-mono text-lg font-semibold">{classroom?.join_code ?? '••••••'}</div>
          </div>
          <Copy className="h-4 w-4 text-muted-foreground" />
        </button>
      </div>

      {/* Roster */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          <Users className="h-4 w-4" /> Students ({roster.length})
        </h2>
        {roster.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              No students yet. Share the join code <span className="font-mono font-semibold">{classroom?.join_code}</span> so students can enroll.
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {roster.map((s) => (
              <Card key={s.enrollment_id}>
                <CardContent className="flex items-center gap-3 p-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
                    {s.username.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">{s.username}</div>
                    <div className="truncate text-xs text-muted-foreground">{s.email}</div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Syllabus */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          <BookOpen className="h-4 w-4" /> Syllabus ({syllabus.length})
        </h2>

        <Card className="mb-3">
          <CardContent className="flex flex-col gap-2 p-4">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              <Input
                placeholder="Subject"
                value={item.subject}
                onChange={(e) => setItem({ ...item, subject: e.target.value })}
              />
              <Input
                placeholder="Chapter *"
                value={item.chapter}
                onChange={(e) => setItem({ ...item, chapter: e.target.value })}
              />
              <Input
                placeholder="Topic (optional)"
                value={item.topic ?? ''}
                onChange={(e) => setItem({ ...item, topic: e.target.value })}
              />
            </div>
            <div>
              <Button
                size="sm"
                className="gap-1"
                disabled={!item.chapter.trim() || addItem.isPending}
                onClick={() => addItem.mutate()}
              >
                <Plus className="h-4 w-4" /> Add chapter
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="flex flex-col gap-2">
          {syllabus.map((s) => (
            <Card key={s.id}>
              <CardContent className="flex items-center gap-3 p-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-medium">{s.chapter}</span>
                    {s.is_published ? (
                      <Badge variant="secondary" className="text-[10px]">Published</Badge>
                    ) : (
                      <Badge variant="outline" className="text-[10px]">Draft</Badge>
                    )}
                  </div>
                  <div className="truncate text-xs text-muted-foreground">
                    {s.subject}
                    {s.topic ? ` · ${s.topic}` : ''}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1"
                  onClick={() => togglePublish.mutate({ id: s.id, publish: !s.is_published })}
                >
                  {s.is_published ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  {s.is_published ? 'Unpublish' : 'Publish'}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-destructive"
                  onClick={() => removeItem.mutate(s.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
