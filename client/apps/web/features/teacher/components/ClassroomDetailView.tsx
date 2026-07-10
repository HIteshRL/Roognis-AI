'use client'

import { useRef, useState, type ReactNode } from 'react'
import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  ArrowLeft,
  BookOpen,
  Copy,
  FileUp,
  Plus,
  RefreshCw,
  Trash2,
  UserMinus,
  Users,
} from 'lucide-react'
import { teacherApi, type Chapter } from '@/lib/api/classroom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Modal } from './Modal'

export function ClassroomDetailView({ classroomId }: { classroomId: string }) {
  const qc = useQueryClient()
  const [addingChapter, setAddingChapter] = useState(false)

  const { data: classroom } = useQuery({
    queryKey: ['teacher', 'classroom', classroomId],
    queryFn: () => teacherApi.getClassroom(classroomId),
    select: (r) => r.data,
  })

  const { data: chapters } = useQuery({
    queryKey: ['teacher', 'classroom', classroomId, 'chapters'],
    queryFn: () => teacherApi.listChapters(classroomId),
    select: (r) => r.data,
  })

  const { data: students } = useQuery({
    queryKey: ['teacher', 'classroom', classroomId, 'students'],
    queryFn: () => teacherApi.listStudents(classroomId),
    select: (r) => r.data,
  })

  const regenerate = useMutation({
    mutationFn: () => teacherApi.regenerateCode(classroomId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['teacher', 'classroom', classroomId] })
      toast.success('New class code generated')
    },
  })

  const removeStudent = useMutation({
    mutationFn: (studentId: string) => teacherApi.removeStudent(classroomId, studentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['teacher', 'classroom', classroomId, 'students'] })
      toast.success('Student removed')
    },
  })

  const color = classroom?.color ?? '#1967d2'

  const copyCode = () => {
    if (classroom?.join_code) {
      navigator.clipboard.writeText(classroom.join_code)
      toast.success('Class code copied')
    }
  }

  return (
    <div className="flex flex-col">
      {/* Banner */}
      <div className="px-6 pt-4">
        <Link
          href="/teacher"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Classes
        </Link>
      </div>
      <div
        className="mx-6 mt-3 flex items-end justify-between rounded-xl px-6 py-6 text-white"
        style={{ backgroundColor: color }}
      >
        <div>
          <h1 className="text-2xl font-bold">{classroom?.name ?? 'Class'}</h1>
          <p className="mt-1 text-sm text-white/80">
            {[classroom?.section, classroom?.subject, classroom?.grade && `Grade ${classroom.grade}`]
              .filter(Boolean)
              .join(' · ')}
          </p>
        </div>
        <div className="rounded-lg bg-white/15 px-4 py-2 text-right backdrop-blur">
          <p className="text-[10px] uppercase tracking-wider text-white/70">Class code</p>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xl font-semibold tracking-widest">
              {classroom?.join_code ?? '······'}
            </span>
            <button onClick={copyCode} aria-label="Copy code" className="text-white/80 hover:text-white">
              <Copy className="h-4 w-4" />
            </button>
            <button
              onClick={() => regenerate.mutate()}
              aria-label="Regenerate code"
              className="text-white/80 hover:text-white"
            >
              <RefreshCw className={`h-4 w-4 ${regenerate.isPending ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      <div className="p-6">
        <Tabs defaultValue="chapters">
          <TabsList>
            <TabsTrigger value="chapters">
              <BookOpen className="mr-1.5 h-4 w-4" />
              Chapters ({chapters?.length ?? 0})
            </TabsTrigger>
            <TabsTrigger value="people">
              <Users className="mr-1.5 h-4 w-4" />
              People ({students?.length ?? 0})
            </TabsTrigger>
          </TabsList>

          {/* Chapters */}
          <TabsContent value="chapters" className="mt-4">
            <div className="mb-4 flex justify-end">
              <Button onClick={() => setAddingChapter(true)}>
                <Plus className="mr-1.5 h-4 w-4" />
                Add chapter
              </Button>
            </div>
            {(chapters?.length ?? 0) === 0 ? (
              <EmptyHint
                icon={<BookOpen className="h-8 w-8 text-muted-foreground/40" />}
                text="No chapters yet. Add a chapter, then upload its content for students to learn from."
              />
            ) : (
              <div className="flex flex-col gap-3">
                {chapters!.map((ch) => (
                  <ChapterRow key={ch.id} chapter={ch} classroomId={classroomId} />
                ))}
              </div>
            )}
          </TabsContent>

          {/* People */}
          <TabsContent value="people" className="mt-4">
            {(students?.length ?? 0) === 0 ? (
              <EmptyHint
                icon={<Users className="h-8 w-8 text-muted-foreground/40" />}
                text={`Share the class code ${classroom?.join_code ?? ''} so students can join.`}
              />
            ) : (
              <div className="divide-y rounded-xl border">
                {students!.map((s) => (
                  <div key={s.id} className="flex items-center justify-between px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div
                        className="flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold text-white"
                        style={{ backgroundColor: color }}
                      >
                        {s.username.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-medium">{s.username}</p>
                        <p className="text-xs text-muted-foreground">{s.email}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => removeStudent.mutate(s.id)}
                      className="text-muted-foreground hover:text-destructive"
                      aria-label="Remove student"
                    >
                      <UserMinus className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>

      <AddChapterModal
        classroomId={classroomId}
        open={addingChapter}
        onClose={() => setAddingChapter(false)}
      />
    </div>
  )
}

function ChapterRow({ chapter, classroomId }: { chapter: Chapter; classroomId: string }) {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)

  const invalidate = () =>
    qc.invalidateQueries({ queryKey: ['teacher', 'classroom', classroomId, 'chapters'] })

  const upload = useMutation({
    mutationFn: (file: File) => teacherApi.uploadContent(chapter.id, file),
    onSuccess: () => {
      toast.success('Content uploaded — ingestion started')
      invalidate()
    },
    onError: (e: Error) => toast.error(e.message || 'Upload failed'),
  })

  const remove = useMutation({
    mutationFn: () => teacherApi.deleteChapter(chapter.id),
    onSuccess: () => {
      toast.success('Chapter deleted')
      invalidate()
    },
  })

  return (
    <div className="flex items-center justify-between rounded-xl border bg-card px-4 py-3">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted text-sm font-semibold">
          {chapter.order_index + 1}
        </div>
        <div>
          <p className="text-sm font-medium">{chapter.title}</p>
          <p className="text-xs text-muted-foreground">
            {chapter.document_count} file{chapter.document_count === 1 ? '' : 's'}
            {chapter.description ? ` · ${chapter.description}` : ''}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-1">
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          accept=".pdf,.docx,.pptx,.txt,.md,.png,.jpg,.jpeg,.webp"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) upload.mutate(file)
            e.target.value = ''
          }}
        />
        <Button variant="ghost" size="sm" disabled={upload.isPending} onClick={() => fileRef.current?.click()}>
          <FileUp className="mr-1.5 h-4 w-4" />
          {upload.isPending ? 'Uploading…' : 'Upload'}
        </Button>
        <button
          onClick={() => remove.mutate()}
          className="rounded-md p-2 text-muted-foreground hover:text-destructive"
          aria-label="Delete chapter"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}

function AddChapterModal({
  classroomId,
  open,
  onClose,
}: {
  classroomId: string
  open: boolean
  onClose: () => void
}) {
  const qc = useQueryClient()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')

  const mutation = useMutation({
    mutationFn: () => teacherApi.addChapter(classroomId, { title, description: description || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['teacher', 'classroom', classroomId, 'chapters'] })
      qc.invalidateQueries({ queryKey: ['teacher', 'classroom', classroomId] })
      toast.success('Chapter added')
      setTitle('')
      setDescription('')
      onClose()
    },
    onError: (e: Error) => toast.error(e.message || 'Could not add chapter'),
  })

  return (
    <Modal open={open} onClose={onClose} title="Add chapter">
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault()
          if (title.trim()) mutation.mutate()
        }}
      >
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="title">Chapter title</Label>
          <Input
            id="title"
            placeholder="e.g. Nutrition in Plants"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="description">Description (optional)</Label>
          <Textarea
            id="description"
            placeholder="What this chapter covers…"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="mt-1 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={!title.trim() || mutation.isPending}>
            {mutation.isPending ? 'Adding…' : 'Add chapter'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function EmptyHint({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
      {icon}
      <p className="mt-3 max-w-sm text-sm text-muted-foreground">{text}</p>
    </div>
  )
}
