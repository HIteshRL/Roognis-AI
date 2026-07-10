'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, BookOpen, Sparkles } from 'lucide-react'
import { classroomStudentApi } from '@/lib/api/classroom'

export function StudentClassDetailView({ classroomId }: { classroomId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['student', 'classroom', classroomId, 'chapters'],
    queryFn: () => classroomStudentApi.listChapters(classroomId),
    select: (r) => r.data,
  })

  const chapters = data ?? []

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <Link
          href="/student/classes"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          My Classes
        </Link>
        <h1 className="mt-3 text-2xl font-bold tracking-tight">Chapters</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Pick a chapter to start learning. The tutor answers using only that chapter&apos;s material.
        </p>
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      ) : chapters.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
          <BookOpen className="h-8 w-8 text-muted-foreground/40" />
          <p className="mt-3 max-w-sm text-sm text-muted-foreground">
            Your teacher hasn&apos;t published any chapters yet. Check back soon.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {chapters.map((ch) => (
            <Link
              key={ch.id}
              href={`/chat?chapter=${ch.id}&title=${encodeURIComponent(ch.title)}`}
              className="group flex items-center justify-between rounded-xl border bg-card px-4 py-4 shadow-sm transition-shadow hover:shadow-md"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-sm font-semibold text-primary">
                  {ch.order_index + 1}
                </div>
                <div>
                  <p className="font-medium">{ch.title}</p>
                  {ch.description && (
                    <p className="text-xs text-muted-foreground">{ch.description}</p>
                  )}
                </div>
              </div>
              <span className="flex items-center gap-1.5 text-sm font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
                <Sparkles className="h-4 w-4" />
                Learn
                <ArrowRight className="h-4 w-4" />
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
