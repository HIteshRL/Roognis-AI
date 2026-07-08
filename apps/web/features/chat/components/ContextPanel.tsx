'use client'

import { Activity, BookOpen, Brain, FileText, Sparkles, TrendingUp } from 'lucide-react'
import { useChatStore } from '@/lib/stores/chat.store'
import type { LearningAnalytics, StudentProfile } from '@/lib/api/student'

interface ContextPanelProps {
  profile?: StudentProfile
  analytics?: LearningAnalytics
}

export function ContextPanel({ profile, analytics }: ContextPanelProps) {
  const lastSourceMeta = useChatStore((s) => s.lastSourceMeta)
  const signals = profile?.behavioral_signals
  const sources = lastSourceMeta?.sources ?? []

  return (
    <aside className="flex h-full w-80 flex-col border-l border-border bg-sidebar">
      <div className="flex h-14 items-center gap-2 px-4">
        <Sparkles className="h-5 w-5 text-primary" />
        <span className="font-semibold tracking-tight">Context</span>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto px-4 pb-6">
        {/* ── Sources (RAG) ───────────────────────────────────────────── */}
        <section>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <FileText className="h-3.5 w-3.5" />
            Sources
          </div>
          {sources.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              Curriculum sources for the latest answer appear here.
            </p>
          ) : (
            <div className="space-y-2">
              {sources.map((s, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-border bg-background p-2.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-medium">
                      {s.title || 'Untitled source'}
                    </span>
                    <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                      {Math.round(s.score * 100)}%
                    </span>
                  </div>
                  {(s.subject || s.chapter) && (
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      {[s.subject, s.chapter].filter(Boolean).join(' · ')}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ── Learner snapshot (psychographics) ───────────────────────── */}
        <section>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <Brain className="h-3.5 w-3.5" />
            Your learning
          </div>
          <div className="grid grid-cols-2 gap-2">
            <StatTile
              icon={<TrendingUp className="h-3.5 w-3.5" />}
              label="Avg mastery"
              value={
                analytics ? `${Math.round(analytics.average_mastery)}%` : '—'
              }
            />
            <StatTile
              icon={<Activity className="h-3.5 w-3.5" />}
              label="Streak"
              value={signals ? `${signals.engagement_streak}d` : '—'}
            />
            <StatTile
              icon={<BookOpen className="h-3.5 w-3.5" />}
              label="Style"
              value={signals?.response_pattern ?? 'unknown'}
            />
            <StatTile
              icon={<Sparkles className="h-3.5 w-3.5" />}
              label="Active gaps"
              value={analytics ? String(analytics.active_gaps) : '—'}
            />
          </div>

          {signals?.dominant_subject && (
            <p className="mt-3 text-xs text-muted-foreground">
              Strongest in{' '}
              <span className="font-medium text-foreground">
                {signals.dominant_subject}
              </span>
              .
            </p>
          )}

          {signals?.strengths && signals.strengths.length > 0 && (
            <div className="mt-3">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Strengths
              </span>
              <div className="mt-1 flex flex-wrap gap-1">
                {signals.strengths.slice(0, 4).map((s) => (
                  <span
                    key={s}
                    className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] text-emerald-600 dark:text-emerald-400"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </aside>
  )
}

function StatTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string
}) {
  return (
    <div className="rounded-lg border border-border bg-background p-2.5">
      <div className="flex items-center gap-1 text-muted-foreground">
        {icon}
        <span className="text-[10px] uppercase tracking-wider">{label}</span>
      </div>
      <p className="mt-1 truncate text-sm font-semibold capitalize">{value}</p>
    </div>
  )
}
