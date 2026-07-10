'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { BookOpen, Plus, School } from 'lucide-react'
import { classroomStudentApi, type StudentClassroom } from '@/lib/api/classroom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Modal } from '@/features/teacher/components/Modal'

export function StudentClassesView() {
  const [joining, setJoining] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['student', 'classrooms'],
    queryFn: () => classroomStudentApi.listMyClasses(),
    select: (r) => r.data,
  })

  const classes = data ?? []

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">My Classes</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Join a class with the code your teacher shared, then learn chapter by chapter.
          </p>
        </div>
        <Button onClick={() => setJoining(true)}>
          <Plus className="mr-1.5 h-4 w-4" />
          Join class
        </Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-40 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      ) : classes.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
          <School className="h-10 w-10 text-muted-foreground/50" />
          <p className="mt-4 font-medium">You haven&apos;t joined any classes</p>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            Ask your teacher for the 6-character class code and join to get started.
          </p>
          <Button className="mt-5" onClick={() => setJoining(true)}>
            <Plus className="mr-1.5 h-4 w-4" />
            Join class
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {classes.map((c) => (
            <StudentClassCard key={c.id} classroom={c} />
          ))}
        </div>
      )}

      <JoinClassModal open={joining} onClose={() => setJoining(false)} />
    </div>
  )
}

function StudentClassCard({ classroom }: { classroom: StudentClassroom }) {
  return (
    <Link
      href={`/student/classes/${classroom.id}`}
      className="flex flex-col overflow-hidden rounded-xl border bg-card shadow-sm transition-shadow hover:shadow-md"
    >
      <div className="h-24 px-4 pt-3" style={{ backgroundColor: classroom.color }}>
        <h3 className="truncate text-lg font-semibold text-white">{classroom.name}</h3>
        {classroom.section && <p className="truncate text-sm text-white/80">{classroom.section}</p>}
        <p className="mt-2 text-xs text-white/70">{classroom.teacher_name}</p>
      </div>
      <div className="flex items-center gap-1.5 px-4 py-3 text-xs text-muted-foreground">
        <BookOpen className="h-3.5 w-3.5" />
        {classroom.chapter_count} chapter{classroom.chapter_count === 1 ? '' : 's'}
      </div>
    </Link>
  )
}

function JoinClassModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const [code, setCode] = useState('')

  const mutation = useMutation({
    mutationFn: () => classroomStudentApi.joinClass(code.trim().toUpperCase()),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['student', 'classrooms'] })
      toast.success(`Joined ${res.data.name}`)
      setCode('')
      onClose()
    },
    onError: (e: Error) => toast.error(e.message || 'Invalid class code'),
  })

  return (
    <Modal open={open} onClose={onClose} title="Join class">
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault()
          if (code.trim()) mutation.mutate()
        }}
      >
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="code">Class code</Label>
          <Input
            id="code"
            placeholder="e.g. K7PQXR"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            className="font-mono text-lg tracking-widest"
            maxLength={12}
            autoFocus
          />
          <p className="text-xs text-muted-foreground">
            Ask your teacher for the class code — 6 characters, letters and numbers.
          </p>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={!code.trim() || mutation.isPending}>
            {mutation.isPending ? 'Joining…' : 'Join'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
