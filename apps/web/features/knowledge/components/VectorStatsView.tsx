'use client'

import { useQuery } from '@tanstack/react-query'
import { Database, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { apiClient } from '@/lib/api/client'

export function VectorStatsView() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['vector-stats'],
    queryFn: async () => {
      const res = await apiClient.get<Record<string, unknown>>('/api/v1/admin/vector/stats')
      return res.data
    },
    refetchInterval: 10_000,
  })

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center gap-3">
        <Database className="h-5 w-5 text-primary" />
        <h1 className="text-xl font-semibold">Vector Statistics</h1>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-destructive">
              Could not load vector stats. Ensure Qdrant is running and you have admin access.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {data && Object.entries(data).map(([key, value]) => (
            <Card key={key}>
              <CardHeader className="pb-1">
                <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {key.replace(/_/g, ' ')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {typeof value === 'string' ? (
                  <Badge variant="outline">{value}</Badge>
                ) : (
                  <p className="text-2xl font-bold">{String(value ?? '—')}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
