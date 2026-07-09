'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useChatStore } from '@/lib/stores/chat.store'

interface NewChatDialogProps {
  subjects: string[]
  open: boolean
  onClose: () => void
}

export function NewChatDialog({ subjects, open, onClose }: NewChatDialogProps) {
  const router = useRouter()
  const setPendingChat = useChatStore((s) => s.setPendingChat)
  const setActiveConversation = useChatStore((s) => s.setActiveConversation)
  const setMessages = useChatStore((s) => s.setMessages)
  const [selectedSubject, setSelectedSubject] = useState('')
  const [chapter, setChapter] = useState('')

  if (!open) return null

  const handleStart = () => {
    const subjectValue = selectedSubject.trim() || null
    const chapterValue = chapter.trim() || null
    setPendingChat(subjectValue, chapterValue)
    setActiveConversation(null)
    setMessages([])
    router.push('/chat')
    onClose()
    setSelectedSubject('')
    setChapter('')
  }

  return (
    <div className="border-t border-border bg-sidebar p-3">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-medium">New Conversation</span>
        <button
          onClick={onClose}
          className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="space-y-3">
        <div className="space-y-1.5">
          <Label className="text-xs">Subject</Label>
          {subjects.length > 0 ? (
            <select
              value={selectedSubject}
              onChange={(e) => setSelectedSubject(e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="">Select a subject...</option>
              {subjects.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          ) : (
            <Input
              placeholder="e.g. Mathematics"
              value={selectedSubject}
              onChange={(e) => setSelectedSubject(e.target.value)}
              className="h-9 text-sm"
            />
          )}
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs">Chapter (optional)</Label>
          <Input
            placeholder="e.g. Quadratic Equations"
            value={chapter}
            onChange={(e) => setChapter(e.target.value)}
            className="h-9 text-sm"
          />
        </div>

        <Button onClick={handleStart} size="sm" className="w-full">
          Start Chat
        </Button>
      </div>
    </div>
  )
}
