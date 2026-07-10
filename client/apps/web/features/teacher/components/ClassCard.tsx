'use client'

import Link from 'next/link'
import { BookOpen, MoreVertical, Users } from 'lucide-react'
import type { Classroom } from '@/lib/api/classroom'

/**
 * Google-Classroom-style class card: a coloured banner with the class name and
 * section, an overlapping monogram avatar, and a footer with quick stats.
 */
export function ClassCard({ classroom }: { classroom: Classroom }) {
  const monogram = classroom.name.trim().charAt(0).toUpperCase() || 'C'

  return (
    <Link
      href={`/teacher/${classroom.id}`}
      className="group relative flex flex-col overflow-hidden rounded-xl border bg-card shadow-sm transition-shadow hover:shadow-md"
    >
      {/* Coloured banner */}
      <div className="relative h-[100px] px-4 pt-3" style={{ backgroundColor: classroom.color }}>
        <div className="flex items-start justify-between">
          <div className="min-w-0 pr-8">
            <h3 className="truncate text-lg font-semibold leading-tight text-white">
              {classroom.name}
            </h3>
            {classroom.section && (
              <p className="truncate text-sm text-white/80">{classroom.section}</p>
            )}
            {classroom.subject && (
              <p className="mt-0.5 truncate text-xs text-white/70">{classroom.subject}</p>
            )}
          </div>
          <MoreVertical className="h-5 w-5 shrink-0 text-white/70" />
        </div>

        {/* Monogram avatar overlapping the banner edge */}
        <div
          className="absolute -bottom-7 right-4 flex h-16 w-16 items-center justify-center rounded-full border-4 border-card text-2xl font-semibold text-white"
          style={{ backgroundColor: shade(classroom.color) }}
        >
          {monogram}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 px-4 pb-3 pt-8">
        {classroom.grade && (
          <p className="text-sm text-muted-foreground">Grade {classroom.grade}</p>
        )}
      </div>

      {/* Footer stats */}
      <div className="flex items-center gap-4 border-t px-4 py-2.5 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <Users className="h-3.5 w-3.5" />
          {classroom.student_count}
        </span>
        <span className="flex items-center gap-1.5">
          <BookOpen className="h-3.5 w-3.5" />
          {classroom.chapter_count} chapters
        </span>
        <span className="ml-auto font-mono tracking-wide text-foreground/70">
          {classroom.join_code}
        </span>
      </div>
    </Link>
  )
}

/** Darken a hex colour a touch for the avatar so it reads against the banner. */
function shade(hex: string): string {
  const m = hex.replace('#', '')
  if (m.length !== 6) return hex
  const n = parseInt(m, 16)
  const r = Math.max(0, ((n >> 16) & 0xff) - 28)
  const g = Math.max(0, ((n >> 8) & 0xff) - 28)
  const b = Math.max(0, (n & 0xff) - 28)
  return `rgb(${r}, ${g}, ${b})`
}
