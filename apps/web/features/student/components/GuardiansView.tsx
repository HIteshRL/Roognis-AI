'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Copy, KeyRound, ShieldCheck, UserX, Users } from 'lucide-react'
import { parentApi } from '@/lib/api/parent'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

export function GuardiansView() {
  const qc = useQueryClient()
  const [code, setCode] = useState<string | null>(null)

  const { data: guardians = [], isLoading } = useQuery({
    queryKey: ['student', 'guardians'],
    queryFn: () => parentApi.getGuardians(),
    select: (r) => r.data,
  })

  const issue = useMutation({
    mutationFn: () => parentApi.issueLinkCode(),
    onSuccess: (r) => setCode(r.data.code),
    onError: (e: Error) => toast.error(e.message),
  })

  const revoke = useMutation({
    mutationFn: (parentId: string) => parentApi.revokeGuardian(parentId),
    onSuccess: () => {
      toast.success('Access revoked')
      qc.invalidateQueries({ queryKey: ['student', 'guardians'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const copy = () => {
    if (code) {
      navigator.clipboard.writeText(code)
      toast.success('Code copied')
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Family Access</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Generate a code and share it with a parent so they can follow your progress. You can revoke access anytime.
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-col gap-3 p-6">
          <div className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-primary" />
            <h2 className="font-semibold">Share access</h2>
          </div>
          {code ? (
            <div className="flex flex-col gap-2">
              <p className="text-sm text-muted-foreground">
                Share this code with your parent. It expires in 7 days.
              </p>
              <button
                onClick={copy}
                className="flex items-center justify-between rounded-md border border-input bg-muted/40 px-4 py-3 transition-colors hover:border-primary/50"
              >
                <span className="font-mono text-2xl font-bold tracking-[0.3em]">{code}</span>
                <Copy className="h-5 w-5 text-muted-foreground" />
              </button>
              <Button variant="outline" size="sm" onClick={() => issue.mutate()} disabled={issue.isPending}>
                Generate a new code
              </Button>
            </div>
          ) : (
            <div>
              <p className="mb-3 text-sm text-muted-foreground">
                Generate a one-time code your parent can enter in their Parent Portal.
              </p>
              <Button onClick={() => issue.mutate()} disabled={issue.isPending}>
                Generate access code
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          <Users className="h-4 w-4" /> People with access ({guardians.length})
        </h2>
        {isLoading ? (
          <div className="text-sm text-muted-foreground">Loading…</div>
        ) : guardians.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
              <ShieldCheck className="h-9 w-9 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">No one has access yet.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="flex flex-col gap-2">
            {guardians.map((g) => (
              <Card key={g.link_id}>
                <CardContent className="flex items-center gap-3 p-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
                    {g.username.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{g.username}</div>
                    <div className="truncate text-xs text-muted-foreground">{g.email}</div>
                  </div>
                  <Badge variant="outline" className="text-[10px]">Parent</Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="gap-1 text-destructive"
                    onClick={() => revoke.mutate(g.parent_id)}
                  >
                    <UserX className="h-4 w-4" /> Revoke
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
