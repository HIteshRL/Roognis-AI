'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Loader2, Search, BookOpen, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { knowledgeApi } from '@/lib/api/knowledge'
import { searchApi, type SearchResultItem } from '@/lib/api/search'

export function SearchPlayground() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResultItem[]>([])
  const [searching, setSearching] = useState(false)
  const [selectedKb, setSelectedKb] = useState<string>('')
  const [topK, setTopK] = useState(5)
  const [threshold, setThreshold] = useState(0.35)

  const { data: kbs } = useQuery({
    queryKey: ['knowledge-bases'],
    queryFn: () => knowledgeApi.listKnowledgeBases(),
    select: (r) => r.data,
  })

  const handleSearch = async () => {
    if (!query.trim()) return
    setSearching(true)
    try {
      const res = await searchApi.search(query, selectedKb || undefined, topK, threshold)
      setResults(res.data.results)
    } catch {
      setResults([])
    } finally {
      setSearching(false)
    }
  }

  return (
    <div className="flex h-full flex-col gap-4 p-6">
      <div className="flex items-center gap-3">
        <Search className="h-5 w-5 text-primary" />
        <h1 className="text-xl font-semibold">Search Playground</h1>
      </div>

      {/* Controls */}
      <Card>
        <CardContent className="flex flex-col gap-4 pt-4">
          <div className="space-y-1.5">
            <Label>Query</Label>
            <Textarea
              rows={3}
              placeholder="Enter a question or topic to search the knowledge base..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSearch())}
            />
          </div>
          <div className="flex flex-wrap gap-4">
            <div className="space-y-1">
              <Label className="text-xs">Knowledge base</Label>
              <select
                className="flex h-8 rounded-md border border-input bg-transparent px-2 text-xs focus-visible:outline-none focus-visible:ring-1"
                value={selectedKb}
                onChange={(e) => setSelectedKb(e.target.value)}
              >
                <option value="">All knowledge bases</option>
                {kbs?.map((kb) => <option key={kb.id} value={kb.id}>{kb.name}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Top-K results</Label>
              <input
                type="number" min={1} max={20}
                className="flex h-8 w-16 rounded-md border border-input bg-transparent px-2 text-xs"
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Min score ({threshold})</Label>
              <input
                type="range" min={0} max={1} step={0.05}
                className="w-32"
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
              />
            </div>
          </div>
          <Button onClick={handleSearch} disabled={!query.trim() || searching} className="w-fit">
            {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Search
          </Button>
        </CardContent>
      </Card>

      {/* Results */}
      {results.length === 0 && !searching ? (
        <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
          <BookOpen className="h-8 w-8 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">Results will appear here after a search.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-3 overflow-y-auto">
          <p className="text-xs text-muted-foreground">{results.length} result{results.length !== 1 ? 's' : ''} found</p>
          {results.map((r, i) => (
            <Card key={r.chunk_id}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <CardTitle className="text-sm">
                      {r.document_title ?? `Document ${r.document_id.slice(0, 8)}`}
                    </CardTitle>
                    {r.page_number && (
                      <span className="text-xs text-muted-foreground">p.{r.page_number}</span>
                    )}
                  </div>
                  <Badge variant="outline" className="text-xs shrink-0">
                    score {r.score.toFixed(3)}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-muted-foreground line-clamp-6 whitespace-pre-wrap">
                  {r.content}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
