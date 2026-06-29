'use client'

import { useEffect } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTheme } from 'next-themes'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { userApi } from '@/lib/api/user'

const schema = z.object({
  theme: z.enum(['light', 'dark', 'system']),
  notifications_enabled: z.boolean(),
  llm_model: z.string().min(1),
  temperature: z.number().min(0).max(2),
})
type FormValues = z.infer<typeof schema>

const LLM_MODELS = [
  { value: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B (default)' },
  { value: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B (fast)' },
  { value: 'mixtral-8x7b-32768', label: 'Mixtral 8x7B' },
]

export function SettingsView() {
  const qc = useQueryClient()
  const { setTheme } = useTheme()

  const { data: settingsData, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => userApi.getSettings(),
    select: (r) => r.data,
  })

  const mutation = useMutation({
    mutationFn: (data: FormValues) => userApi.updateSettings(data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['settings'] })
      setTheme(res.data.theme)
      toast.success('Settings saved')
    },
    onError: () => toast.error('Failed to save settings'),
  })

  const { register, handleSubmit, reset, control } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  useEffect(() => {
    if (settingsData) {
      reset({
        theme: settingsData.theme as 'light' | 'dark' | 'system',
        notifications_enabled: settingsData.notifications_enabled,
        llm_model: settingsData.llm_model,
        temperature: settingsData.temperature,
      })
    }
  }, [settingsData, reset])

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-xl p-6">
      <h1 className="mb-6 text-xl font-semibold">Settings</h1>
      <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Appearance</CardTitle>
            <CardDescription>Choose your preferred theme.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              <Label>Theme</Label>
              <select
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                {...register('theme')}
              >
                <option value="dark">Dark</option>
                <option value="light">Light</option>
                <option value="system">System</option>
              </select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">AI Model</CardTitle>
            <CardDescription>Select the LLM used for your conversations.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Model</Label>
              <select
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                {...register('llm_model')}
              >
                {LLM_MODELS.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>Temperature ({settingsData?.temperature ?? 0.7})</Label>
              <Controller
                control={control}
                name="temperature"
                render={({ field }) => (
                  <input
                    type="range"
                    min={0}
                    max={2}
                    step={0.1}
                    className="w-full"
                    value={field.value}
                    onChange={(e) => field.onChange(parseFloat(e.target.value))}
                  />
                )}
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Precise</span>
                <span>Creative</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
          Save settings
        </Button>
      </form>
    </div>
  )
}
