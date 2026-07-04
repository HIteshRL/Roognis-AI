'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { BookOpen, GraduationCap, LogIn, School as SchoolIcon } from 'lucide-react'
import { schoolApi } from '@/lib/api/school'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'

function ClassroomSyllabus({ classroomId }: { classroomId: string }) {
  const { data: items = [], isLoading } = useQuery({
    queryKey: ['school', 'student-syllabus', classroomId],
    queryFn: () => schoolApi.getSyllabus(classroomId),
    select: (r) => r.data,
  })

  if (isLoading) {
    return <p className="text-xs text-muted-foreground">Loading syllabus…</p>
  }
  if (items.length === 0) {
    return <p className="text-xs text-muted-foreground">No published chapters yet.</p>
  }
  return (
    <div className="flex flex-col gap-1.5">
      {items.map((s) => (
        <div key={s.id} className="flex items-center gap-2 rounded-md bg-muted/50 px-3 py-2">
          <BookOpen className="h-3.5 w-3.5 shrink-0 text-primary" />
          <div className="min-w-0">
            <div className="truncate text-sm font-medium">{s.chapter}</div>
            {s.topic && <div className="truncate text-xs text-muted-foreground">{s.topic}</div>}
          </div>
          <Badge variant="outline" className="ml-auto text-[10px]">
            {s.subject}
          </Badge>
        </div>
      ))}
    </div>
  )
}

export function MyClassesView() {
  const qc = useQueryClient()
  const [code, setCode] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)

  const { data: classrooms = [], isLoading } = useQuery({
    queryKey: ['school', 'enrolled'],
    queryFn: () => schoolApi.getEnrolledClassrooms(),
    select: (r) => r.data,
  })

  const join = useMutation({
    mutationFn: () => schoolApi.joinClassroom(code.trim().toUpperCase()),
    onSuccess: (r) => {
      toast.success(`Joined ${r.data.name}`)
      setCode('')
      qc.invalidateQueries({ queryKey: ['school', 'enrolled'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">My Classes</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Join your school classrooms and follow the published syllabus.
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2 text-sm font-medium">
            <LogIn className="h-4 w-4 text-primary" /> Join a class
          </div>
          <div className="flex flex-1 gap-2">
            <Input
              placeholder="Enter join code (e.g. ABC123)"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              className="font-mono uppercase"
              maxLength={16}
            />
            <Button disabled={!code.trim() || join.isPending} onClick={() => join.mutate()}>
              Join
            </Button>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading your classes…</div>
      ) : classrooms.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
            <GraduationCap className="h-10 w-10 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              You haven&apos;t joined any classes yet. Ask your teacher for a join code.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {classrooms.map((c) => (
            <Card key={c.id}>
              <CardContent className="p-4">
                <button
                  className="flex w-full items-center gap-3 text-left"
                  onClick={() => setExpanded(expanded === c.id ? null : c.id)}
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <SchoolIcon className="h-5 w-5 text-primary" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-semibold">{c.name}</div>
                    <div className="truncate text-xs text-muted-foreground">
                      {c.subject ?? 'General'}
                      {c.grade ? ` · Grade ${c.grade}` : ''} · {c.syllabus_count} chapters
                    </div>
                  </div>
                  <Badge variant="secondary">{expanded === c.id ? 'Hide' : 'View'}</Badge>
                </button>
                {expanded === c.id && (
                  <div className="mt-3 border-t pt-3">
                    <ClassroomSyllabus classroomId={c.id} />
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
