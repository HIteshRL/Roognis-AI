'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Search, ChevronDown, ChevronUp, Clock, Layers, BookOpen, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

// ── Schema ────────────────────────────────────────────────────────────────────

const schema = z.object({
  query: z.string().min(1, 'Query is required'),
  grade: z.string().optional(),
  subject: z.string().optional(),
  chapter: z.string().optional(),
  topic: z.string().optional(),
  institution: z.string().optional(),
  top_k: z.number().int().min(1).max(20).default(5),
  score_threshold: z.number().min(0).max(1).default(0.35),
})

type FormValues = z.infer<typeof schema>

// ── Types ─────────────────────────────────────────────────────────────────────

interface RagChunk {
  chunk_id: string
  document_id: string
  document_title: string | null
  content: string
  score: number
  page_number: number | null
  grade: string | null
  subject: string | null
  chapter: string | null
  topic: string | null
}

interface Observability {
  embedding_ms: number
  retrieval_ms: number
  llm_ms: number
  total_ms: number
  chunks_retrieved: number
  chunks_used: number
  similarity_scores: number[]
  token_usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number }
}

interface RagResult {
  query: string
  answer: string
  has_context: boolean
  chunks: RagChunk[]
  curriculum_filter: Record<string, string>
  observability: Observability
}

// ── Component ─────────────────────────────────────────────────────────────────

export function RagConsole() {
  const [result, setResult] = useState<RagResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(new Set())

  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { top_k: 5, score_threshold: 0.35 },
  })

  const onSubmit = async (values: FormValues) => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const curriculum: Record<string, string> = {}
      if (values.grade) curriculum.grade = values.grade
      if (values.subject) curriculum.subject = values.subject
      if (values.chapter) curriculum.chapter = values.chapter
      if (values.topic) curriculum.topic = values.topic
      if (values.institution) curriculum.institution = values.institution

      const res = await fetch('/api/v1/rag/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: values.query,
          curriculum,
          top_k: values.top_k,
          score_threshold: values.score_threshold,
          include_chunks: true,
        }),
      })

      const body = await res.json()
      if (!body.success) throw new Error(body.message || 'Query failed')
      setResult(body.data as RagResult)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const toggleChunk = (id: string) => {
    setExpandedChunks(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  return (
    <div className="flex flex-col gap-6 p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold">RAG Test Console</h1>
        <p className="text-sm text-muted-foreground">
          Test curriculum-filtered retrieval. The LLM answers only from matching curriculum content.
        </p>
      </div>

      {/* Query Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Curriculum Query</CardTitle>
          <CardDescription className="text-xs">
            Set curriculum filters to constrain retrieval to specific academic content.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
            {/* Question */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium">Question *</label>
              <textarea
                {...register('query')}
                rows={3}
                placeholder="e.g. What is photosynthesis?"
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
              />
              {errors.query && (
                <span className="text-xs text-destructive">{errors.query.message}</span>
              )}
            </div>

            {/* Curriculum filters */}
            <div className="rounded-md border border-border p-3 flex flex-col gap-3">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                Curriculum Filters
              </span>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {[
                  { name: 'institution' as const, placeholder: 'e.g. MIT' },
                  { name: 'grade' as const, placeholder: 'e.g. 7 or Grade 7' },
                  { name: 'subject' as const, placeholder: 'e.g. Science' },
                  { name: 'chapter' as const, placeholder: 'e.g. Nutrition in Plants' },
                  { name: 'topic' as const, placeholder: 'e.g. Photosynthesis' },
                ].map(({ name, placeholder }) => (
                  <div key={name} className="flex flex-col gap-1">
                    <label className="text-xs font-medium capitalize">{name}</label>
                    <input
                      {...register(name)}
                      placeholder={placeholder}
                      className="rounded-md border border-border bg-background px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Advanced */}
            <div className="flex gap-4">
              <div className="flex flex-col gap-1 w-28">
                <label className="text-xs font-medium">Top K</label>
                <input
                  type="number"
                  {...register('top_k', { valueAsNumber: true })}
                  min={1}
                  max={20}
                  className="rounded-md border border-border bg-background px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div className="flex flex-col gap-1 w-36">
                <label className="text-xs font-medium">Score Threshold</label>
                <input
                  type="number"
                  step="0.05"
                  {...register('score_threshold', { valueAsNumber: true })}
                  min={0}
                  max={1}
                  className="rounded-md border border-border bg-background px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>

            <Button type="submit" disabled={loading} className="w-fit gap-2">
              <Search className="h-4 w-4" />
              {loading ? 'Querying…' : 'Run Query'}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Observability bar */}
          <div className="flex flex-wrap gap-4 rounded-md border border-border bg-muted/30 px-4 py-3 text-xs">
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-muted-foreground">Embed</span>
              <span className="font-mono font-medium">{result.observability.embedding_ms.toFixed(0)}ms</span>
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-muted-foreground">Retrieve</span>
              <span className="font-mono font-medium">{result.observability.retrieval_ms.toFixed(0)}ms</span>
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-muted-foreground">LLM</span>
              <span className="font-mono font-medium">{result.observability.llm_ms.toFixed(0)}ms</span>
            </span>
            <span className="flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-muted-foreground">Chunks</span>
              <span className="font-mono font-medium">
                {result.observability.chunks_used}/{result.observability.chunks_retrieved}
              </span>
            </span>
            <span className="flex items-center gap-1.5">
              <BookOpen className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-muted-foreground">Tokens</span>
              <span className="font-mono font-medium">{result.observability.token_usage.total_tokens}</span>
            </span>
            {Object.entries(result.curriculum_filter).length > 0 && (
              <span className="ml-auto flex items-center gap-1 text-muted-foreground">
                Filter:
                {Object.entries(result.curriculum_filter).map(([k, v]) => (
                  <span key={k} className="rounded bg-primary/10 px-1.5 py-0.5 font-medium text-primary">
                    {k}={v}
                  </span>
                ))}
              </span>
            )}
          </div>

          {/* Answer */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                Answer
                {!result.has_context && (
                  <span className="text-xs font-normal text-amber-500 bg-amber-500/10 rounded px-2 py-0.5">
                    No curriculum context
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{result.answer}</p>
            </CardContent>
          </Card>

          {/* Retrieved Chunks */}
          {result.chunks.length > 0 && (
            <div className="flex flex-col gap-2">
              <h2 className="text-sm font-semibold">
                Retrieved Chunks ({result.chunks.length})
              </h2>
              {result.chunks.map((chunk, i) => (
                <div
                  key={chunk.chunk_id}
                  className="rounded-md border border-border overflow-hidden"
                >
                  <button
                    type="button"
                    onClick={() => toggleChunk(chunk.chunk_id)}
                    className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-mono text-muted-foreground">#{i + 1}</span>
                      <span className="text-sm font-medium">
                        {chunk.document_title ?? 'Untitled'}
                      </span>
                      {chunk.page_number && (
                        <span className="text-xs text-muted-foreground">p.{chunk.page_number}</span>
                      )}
                      {[chunk.grade, chunk.subject, chunk.chapter].filter(Boolean).map((tag) => (
                        <span
                          key={tag}
                          className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-medium"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-mono font-semibold text-primary">
                        {(chunk.score * 100).toFixed(1)}%
                      </span>
                      {expandedChunks.has(chunk.chunk_id)
                        ? <ChevronUp className="h-4 w-4 text-muted-foreground" />
                        : <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      }
                    </div>
                  </button>

                  {expandedChunks.has(chunk.chunk_id) && (
                    <div className="border-t border-border bg-muted/20 px-4 py-3">
                      <p className="text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap">
                        {chunk.content}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
