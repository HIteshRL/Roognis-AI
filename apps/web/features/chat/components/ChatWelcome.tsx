'use client'

import {
  Atom,
  BookOpen,
  Calculator,
  Code2,
  FlaskConical,
  Globe2,
  Languages,
  Sparkles,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

interface Suggestion {
  icon: LucideIcon
  label: string
  prompt: string
}

const GENERAL_SUGGESTIONS: Suggestion[] = [
  {
    icon: FlaskConical,
    label: 'Biology',
    prompt: 'Explain how the human heart pumps blood, and describe the diagram.',
  },
  {
    icon: Calculator,
    label: 'Mathematics',
    prompt: 'Walk me through solving the quadratic equation x² − 5x + 6 = 0, step by step.',
  },
  {
    icon: Globe2,
    label: 'Social Studies',
    prompt: 'What were the main causes of the First World War?',
  },
  {
    icon: Code2,
    label: 'Computers',
    prompt: 'How does a for-loop work in Python? Give me a simple example.',
  },
]

const SUBJECT_ICONS: Record<string, LucideIcon> = {
  physics: Atom,
  chemistry: FlaskConical,
  biology: FlaskConical,
  mathematics: Calculator,
  maths: Calculator,
  math: Calculator,
  english: Languages,
  languages: Languages,
  'social studies': Globe2,
  history: Globe2,
  geography: Globe2,
  computers: Code2,
  'computer science': Code2,
}

function subjectSuggestions(subject: string): Suggestion[] {
  const icon = SUBJECT_ICONS[subject.toLowerCase()] ?? BookOpen
  return [
    { icon, label: 'Explain', prompt: `Explain a core concept from ${subject} in simple terms.` },
    { icon, label: 'Example', prompt: `Give me a worked example from ${subject}.` },
    { icon, label: 'Quiz me', prompt: `Ask me a practice question about ${subject}.` },
    { icon, label: 'Where I struggle', prompt: `What should I revise in ${subject}?` },
  ]
}

interface ChatWelcomeProps {
  subject?: string | null
  chapter?: string | null
  onPick: (prompt: string) => void
}

export function ChatWelcome({ subject, chapter, onPick }: ChatWelcomeProps) {
  const suggestions = subject ? subjectSuggestions(subject) : GENERAL_SUGGESTIONS

  return (
    <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center px-4 text-center">
      <div className="relative mb-6">
        <div className="absolute inset-0 animate-ping rounded-2xl bg-primary/20 [animation-duration:2.5s]" />
        <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-sky-500 shadow-xl shadow-primary/30 ring-1 ring-white/20">
          <Sparkles className="h-8 w-8 text-white" />
        </div>
      </div>

      <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
        {subject ? (
          <>
            Let&apos;s dive into <span className="text-gradient">{subject}</span>
          </>
        ) : (
          <>
            What would you like to <span className="text-gradient">learn</span> today?
          </>
        )}
      </h1>
      <p className="mt-3 max-w-md text-sm text-muted-foreground">
        {chapter
          ? `Ask anything about ${chapter} — I'll explain it your way, with examples and diagrams.`
          : 'Your AI tutor adapts to how you learn. Ask a question, or start with one of these.'}
      </p>

      <div className="mt-8 grid w-full grid-cols-1 gap-3 sm:grid-cols-2">
        {suggestions.map((s) => (
          <button
            key={s.prompt}
            onClick={() => onPick(s.prompt)}
            className="group flex items-start gap-3 rounded-2xl border border-border/70 bg-card/60 p-4 text-left backdrop-blur transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:bg-card hover:shadow-lg hover:shadow-primary/5"
          >
            <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary/15">
              <s.icon className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-primary">{s.label}</p>
              <p className="mt-0.5 line-clamp-2 text-sm text-foreground/90">{s.prompt}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
