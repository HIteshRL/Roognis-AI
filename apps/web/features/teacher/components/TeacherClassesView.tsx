'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus, School } from 'lucide-react'
import { teacherApi } from '@/lib/api/classroom'
import { Button } from '@/components/ui/button'
import { ClassCard } from './ClassCard'
import { CreateClassModal } from './CreateClassModal'

export function TeacherClassesView() {
  const [creating, setCreating] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['teacher', 'classrooms'],
    queryFn: () => teacherApi.listClassrooms(),
    select: (r) => r.data,
  })

  const classrooms = data ?? []

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Classes</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Create subjects, add chapters, and share the class code with students.
          </p>
        </div>
        <Button onClick={() => setCreating(true)}>
          <Plus className="mr-1.5 h-4 w-4" />
          Create class
        </Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-52 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      ) : classrooms.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
          <School className="h-10 w-10 text-muted-foreground/50" />
          <p className="mt-4 font-medium">No classes yet</p>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            Create your first class to start uploading chapter content for your students.
          </p>
          <Button className="mt-5" onClick={() => setCreating(true)}>
            <Plus className="mr-1.5 h-4 w-4" />
            Create class
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {classrooms.map((c) => (
            <ClassCard key={c.id} classroom={c} />
          ))}
        </div>
      )}

      <CreateClassModal open={creating} onClose={() => setCreating(false)} />
    </div>
  )
}
