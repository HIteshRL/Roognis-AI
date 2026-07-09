'use client'

import { useQuery } from '@tanstack/react-query'
import { Activity, AlertTriangle, BarChart3, TrendingUp, Users } from 'lucide-react'
import { schoolApi, type MasteryBucket } from '@/lib/api/school'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

const BUCKET_STYLE: Record<string, { label: string; color: string }> = {
  struggling: { label: 'Struggling', color: 'bg-red-500' },
  developing: { label: 'Developing', color: 'bg-orange-400' },
  proficient: { label: 'Proficient', color: 'bg-sky-500' },
  mastered: { label: 'Mastered', color: 'bg-green-500' },
  no_data: { label: 'No data', color: 'bg-muted-foreground/40' },
}

function Stat({ icon: Icon, label, value }: { icon: typeof Users; label: string; value: string | number }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-4 w-4 text-primary" />
        </div>
        <div>
          <div className="text-lg font-semibold leading-none">{value}</div>
          <div className="text-xs text-muted-foreground">{label}</div>
        </div>
      </CardContent>
    </Card>
  )
}

function DistributionBar({ buckets, total }: { buckets: MasteryBucket[]; total: number }) {
  if (total === 0) return null
  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full">
        {buckets.map((b) =>
          b.count > 0 ? (
            <div
              key={b.label}
              className={BUCKET_STYLE[b.label]?.color ?? 'bg-muted'}
              style={{ width: `${(b.count / total) * 100}%` }}
              title={`${BUCKET_STYLE[b.label]?.label ?? b.label}: ${b.count}`}
            />
          ) : null
        )}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
        {buckets.map((b) => (
          <span key={b.label} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className={`h-2 w-2 rounded-full ${BUCKET_STYLE[b.label]?.color ?? 'bg-muted'}`} />
            {BUCKET_STYLE[b.label]?.label ?? b.label} ({b.count})
          </span>
        ))}
      </div>
    </div>
  )
}

export function ClassroomAnalyticsView({ classroomId }: { classroomId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['school', 'analytics', classroomId],
    queryFn: () => schoolApi.getClassroomAnalytics(classroomId),
    select: (r) => r.data,
  })

  return (
    <div>
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        <BarChart3 className="h-4 w-4" /> Class Analytics
      </h2>

      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading analytics…</div>
      ) : !data || data.student_count === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            Analytics appear once students enroll and start learning.
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Stat icon={Users} label="Students" value={data.student_count} />
            <Stat icon={TrendingUp} label="Class avg mastery" value={`${Math.round(data.class_avg_mastery)}%`} />
            <Stat icon={Activity} label="Total sessions" value={data.total_sessions} />
            <Stat icon={AlertTriangle} label="Top gaps" value={data.top_misconceptions.length} />
          </div>

          <Card>
            <CardContent className="p-4">
              <div className="mb-2 text-sm font-medium">Mastery distribution</div>
              <DistributionBar buckets={data.mastery_distribution} total={data.student_count} />
            </CardContent>
          </Card>

          {data.top_misconceptions.length > 0 && (
            <Card>
              <CardContent className="p-4">
                <div className="mb-2 flex items-center gap-1.5 text-sm font-medium">
                  <AlertTriangle className="h-4 w-4 text-orange-400" /> Common weak concepts
                </div>
                <div className="flex flex-col gap-1.5">
                  {data.top_misconceptions.map((m) => (
                    <div key={m.concept_name} className="flex items-center justify-between text-sm">
                      <span>{m.concept_name}</span>
                      <Badge variant="outline" className="text-[10px]">
                        {m.student_count} {m.student_count === 1 ? 'student' : 'students'}
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 font-medium">Student</th>
                  <th className="px-3 py-2 font-medium">Mastery</th>
                  <th className="px-3 py-2 font-medium">Gaps</th>
                  <th className="px-3 py-2 font-medium">Sessions</th>
                  <th className="px-3 py-2 font-medium">Last active</th>
                </tr>
              </thead>
              <tbody>
                {data.students.map((s) => (
                  <tr key={s.student_id} className="border-t">
                    <td className="px-3 py-2">
                      <div className="font-medium">{s.username}</div>
                      <div className="text-xs text-muted-foreground">{s.email}</div>
                    </td>
                    <td className="px-3 py-2">{Math.round(s.avg_mastery)}%</td>
                    <td className="px-3 py-2">
                      {s.active_gap_count > 0 ? (
                        <Badge variant="outline" className="text-[10px] text-orange-500">
                          {s.active_gap_count}
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground">0</span>
                      )}
                    </td>
                    <td className="px-3 py-2">{s.session_count}</td>
                    <td className="px-3 py-2 text-muted-foreground">
                      {s.last_activity ? new Date(s.last_activity).toLocaleDateString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
