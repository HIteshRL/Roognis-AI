'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { teacherApi, type CreateClassroomPayload } from '@/lib/api/classroom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Modal } from './Modal'

const COLORS = [
  '#1967d2', '#1e8e3e', '#e52592', '#9334e6',
  '#e8710a', '#00897b', '#d93025', '#3949ab',
]

export function CreateClassModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<CreateClassroomPayload>({ name: '', color: COLORS[0] })

  const mutation = useMutation({
    mutationFn: () => teacherApi.createClassroom(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['teacher', 'classrooms'] })
      toast.success('Class created')
      setForm({ name: '', color: COLORS[0] })
      onClose()
    },
    onError: (e: Error) => toast.error(e.message || 'Could not create class'),
  })

  const set = (k: keyof CreateClassroomPayload, v: string) => setForm((f) => ({ ...f, [k]: v }))

  return (
    <Modal open={open} onClose={onClose} title="Create class">
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault()
          if (!form.name.trim()) return
          mutation.mutate()
        }}
      >
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="name">Class name (required)</Label>
          <Input
            id="name"
            placeholder="e.g. Grade 7 Science"
            value={form.name}
            onChange={(e) => set('name', e.target.value)}
            autoFocus
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="subject">Subject</Label>
            <Input id="subject" placeholder="Science" value={form.subject ?? ''} onChange={(e) => set('subject', e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="grade">Grade</Label>
            <Input id="grade" placeholder="7" value={form.grade ?? ''} onChange={(e) => set('grade', e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="section">Section</Label>
            <Input id="section" placeholder="A" value={form.section ?? ''} onChange={(e) => set('section', e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="room">Room</Label>
            <Input id="room" placeholder="Lab 2" value={form.room ?? ''} onChange={(e) => set('room', e.target.value)} />
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Theme colour</Label>
          <div className="flex flex-wrap gap-2">
            {COLORS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => set('color', c)}
                className={`h-8 w-8 rounded-full transition-transform ${form.color === c ? 'ring-2 ring-offset-2 ring-foreground scale-110' : ''}`}
                style={{ backgroundColor: c }}
                aria-label={`Colour ${c}`}
              />
            ))}
          </div>
        </div>

        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={!form.name.trim() || mutation.isPending}>
            {mutation.isPending ? 'Creating…' : 'Create'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
