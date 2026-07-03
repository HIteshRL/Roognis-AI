import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { chatApi } from '@/lib/api/chat'
import type { MediaJobDto } from '@roognis/shared'

/**
 * Requests on-demand video generation for an assistant message and polls the
 * job until it reaches a terminal state. The completed job carries the
 * attachment id, which the caller renders inline (no conversation reload).
 */
export function useVideoJob(messageId: string) {
  const [jobId, setJobId] = useState<string | null>(null)

  const request = useMutation({
    mutationFn: () => chatApi.requestVideo(messageId),
    onSuccess: (r) => setJobId(r.data.id),
    onError: () => toast.error('Could not start video generation'),
  })

  const { data: job } = useQuery({
    queryKey: ['media-job', jobId],
    queryFn: () => chatApi.getMediaJob(jobId as string),
    select: (r) => r.data,
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = (query.state.data as { data?: MediaJobDto } | undefined)?.data?.status
      return status === 'completed' || status === 'failed' ? false : 2000
    },
  })

  return {
    start: () => request.mutate(),
    isStarting: request.isPending,
    job: job ?? null,
    isActive: !!jobId && job?.status !== 'completed' && job?.status !== 'failed',
  }
}
