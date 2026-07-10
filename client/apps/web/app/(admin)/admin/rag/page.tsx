import type { Metadata } from 'next'
import { RagConsole } from '@/features/rag/components/RagConsole'

export const metadata: Metadata = { title: 'RAG Console — Roognis AI' }

export default function RagConsolePage() {
  return <RagConsole />
}
