import { apiClient } from './client'

export interface SearchResultItem {
  chunk_id: string
  document_id: string
  document_title: string | null
  content: string
  score: number
  page_number: number | null
  metadata: Record<string, unknown>
}

export interface SearchResponse {
  query: string
  results: SearchResultItem[]
  total_found: number
  knowledge_base_id: string | null
}

export const searchApi = {
  search: (query: string, knowledgeBaseId?: string, topK = 5, scoreThreshold = 0.35) =>
    apiClient.post<SearchResponse>('/api/v1/search', {
      query,
      knowledge_base_id: knowledgeBaseId ?? null,
      top_k: topK,
      score_threshold: scoreThreshold,
    }),
}
