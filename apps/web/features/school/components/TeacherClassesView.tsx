'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { toast } from 'sonner'
import { GraduationCap, Plus, School as SchoolIcon, Users, BookOpen, ArrowRight } from 'lucide-react'
import { schoolApi, type CreateClassroomPayload } from '@/lib/api/school'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'

export function TeacherClassesView() {
  const qc = useQueryClient()
  const [schoolName, setSchoolName] = useState('')
  const [form, setForm] = useState<CreateClassroomPayload>({
    school_id: '',
    name: '',
    subject: '',
    grade: '',
  })

  const { data: schools = [], isLoading: schoolsLoading } = useQuery({
    queryKey: ['school', 'mine'],
    queryFn: () => schoolApi.getMySchools(),
    select: (r) => r.data,
  })

  const { data: classrooms = [], isLoading: classesLoading } = useQuery({
    queryKey: ['school', 'classrooms', 'mine'],
    queryFn: () => schoolApi.getMyClassrooms(),
    select: (r) => r.data,
  })

  const createSchool = useMutation({
    mutationFn: () => schoolApi.createSchool(schoolName.trim()),
    onSuccess: () => {
      toast.success('School created')
      setSchoolName('')
      qc.invalidateQueries({ queryKey: ['school', 'mine'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const createClassroom = useMutation({
    mutationFn: () =>
      schoolApi.createClassroom({
        ...form,
        school_id: form.school_id || schools[0]?.id || '',
      }),
    onSuccess: () => {
      toast.success('Classroom created')
      setForm({ school_id: schools[0]?.id ?? '', name: '', subject: '', grade: '' })
      qc.invalidateQueries({ queryKey: ['school', 'classrooms', 'mine'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  if (schoolsLoading) {
    return <div className="p-6 text-sm text-muted-foreground">Loading…</div>
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Teacher Portal</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Create classrooms, share join codes, and publish your syllabus to students.
        </p>
      </div>

      {schools.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col gap-3 p-6">
            <div className="flex items-center gap-2">
              <SchoolIcon className="h-5 w-5 text-primary" />
              <h2 className="font-semibold">Create your school</h2>
            </div>
            <p className="text-sm text-muted-foreground">
              A school is the top-level organization that holds your classrooms.
            </p>
            <div className="flex gap-2">
              <Input
                placeholder="e.g. Green Valley High"
                value={schoolName}
                onChange={(e) => setSchoolName(e.target.value)}
              />
              <Button
                disabled={!schoolName.trim() || createSchool.isPending}
                onClick={() => createSchool.mutate()}
              >
                Create
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="flex flex-col gap-3 p-6">
            <div className="flex items-center gap-2">
              <Plus className="h-5 w-5 text-primary" />
              <h2 className="font-semibold">New classroom</h2>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-4">
              {schools.length > 1 && (
                <select
                  className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={form.school_id || schools[0].id}
                  onChange={(e) => setForm({ ...form, school_id: e.target.value })}
                >
                  {schools.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              )}
              <Input
                placeholder="Class name *"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
              <Input
                placeholder="Subject"
                value={form.subject ?? ''}
                onChange={(e) => setForm({ ...form, subject: e.target.value })}
              />
              <Input
                placeholder="Grade"
                value={form.grade ?? ''}
                onChange={(e) => setForm({ ...form, grade: e.target.value })}
              />
            </div>
            <div>
              <Button
                disabled={!form.name.trim() || createClassroom.isPending}
                onClick={() => createClassroom.mutate()}
              >
                Create classroom
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Your classrooms
        </h2>
        {classesLoading ? (
          <div className="text-sm text-muted-foreground">Loading classrooms…</div>
        ) : classrooms.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
              <GraduationCap className="h-10 w-10 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                No classrooms yet. Create one above to get started.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {classrooms.map((c) => (
              <Link key={c.id} href={`/teacher/classes/${c.id}`}>
                <Card className="h-full transition-colors hover:border-primary/50">
                  <CardContent className="flex h-full flex-col gap-3 p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-semibold">{c.name}</h3>
                        <p className="text-xs text-muted-foreground">
                          {c.subject ?? 'General'} {c.grade ? `· Grade ${c.grade}` : ''}
                        </p>
                      </div>
                      <Badge variant="secondary" className="font-mono">
                        {c.join_code}
                      </Badge>
                    </div>
                    <div className="mt-auto flex items-center gap-4 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Users className="h-3.5 w-3.5" /> {c.student_count}
                      </span>
                      <span className="flex items-center gap-1">
                        <BookOpen className="h-3.5 w-3.5" /> {c.syllabus_count}
                      </span>
                      <ArrowRight className="ml-auto h-4 w-4" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
