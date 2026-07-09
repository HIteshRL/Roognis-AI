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
  FileStack,
  Plus,
  Trash2,
  Users,
} from 'lucide-react'
import { schoolApi, type CreateSyllabusPayload } from '@/lib/api/school'
import { ClassroomAnalyticsView } from './ClassroomAnalyticsView'
import { MaterialsPanel } from './MaterialsPanel'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

// Deterministic banner colour from the class id — Google Classroom vibe.
const BANNERS = [
  'from-sky-500 to-indigo-600',
  'from-emerald-500 to-teal-600',
  'from-violet-500 to-purple-600',
  'from-amber-500 to-orange-600',
  'from-rose-500 to-pink-600',
  'from-cyan-500 to-blue-600',
]
function bannerFor(id: string): string {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0
  return BANNERS[h % BANNERS.length]
}

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
      toast.success('Chapter added')
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
    <div className="mx-auto flex max-w-5xl flex-col gap-5 p-4 sm:p-6">
      <Link href="/teacher" className="w-fit">
        <Button variant="ghost" size="sm" className="gap-1 -ml-2">
          <ArrowLeft className="h-4 w-4" /> Classes
        </Button>
      </Link>

      {/* Google Classroom–style banner */}
      <div
        className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${bannerFor(
          classroomId
        )} p-6 text-white shadow-lg sm:p-8`}
      >
        <div className="absolute -right-8 -top-8 h-40 w-40 rounded-full bg-white/10" />
        <div className="absolute -bottom-12 right-16 h-32 w-32 rounded-full bg-white/5" />
        <div className="relative flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
              {classroom?.name ?? '…'}
            </h1>
            <p className="mt-1 text-sm text-white/85">
              {classroom?.subject ?? 'General'}
              {classroom?.grade ? ` · Grade ${classroom.grade}` : ''}
            </p>
          </div>
          <button
            onClick={copyCode}
            className="flex items-center gap-2 rounded-lg bg-white/15 px-3 py-2 backdrop-blur transition-colors hover:bg-white/25"
          >
            <div className="text-left">
              <div className="text-[10px] uppercase tracking-wider text-white/70">Class code</div>
              <div className="font-mono text-base font-semibold">
                {classroom?.join_code ?? '••••••'}
              </div>
            </div>
            <Copy className="h-4 w-4 text-white/80" />
          </button>
        </div>
      </div>

      <Tabs defaultValue="classwork">
        <TabsList>
          <TabsTrigger value="classwork" className="gap-1.5">
            <FileStack className="h-4 w-4" /> Classwork
          </TabsTrigger>
          <TabsTrigger value="people" className="gap-1.5">
            <Users className="h-4 w-4" /> People ({roster.length})
          </TabsTrigger>
        </TabsList>

        {/* ── Classwork: materials + chapters ─────────────────────────────── */}
        <TabsContent value="classwork" className="mt-4 flex flex-col gap-6">
          <MaterialsPanel classroomId={classroomId} />

          <div>
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              <BookOpen className="h-4 w-4" /> Chapters ({syllabus.length})
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
        </TabsContent>

        {/* ── People: roster + analytics ──────────────────────────────────── */}
        <TabsContent value="people" className="mt-4 flex flex-col gap-6">
          <div>
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              <Users className="h-4 w-4" /> Students ({roster.length})
            </h2>
            {roster.length === 0 ? (
              <Card>
                <CardContent className="py-8 text-center text-sm text-muted-foreground">
                  No students yet. Share the class code{' '}
                  <span className="font-mono font-semibold">{classroom?.join_code}</span> so students
                  can join.
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

          <ClassroomAnalyticsView classroomId={classroomId} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
