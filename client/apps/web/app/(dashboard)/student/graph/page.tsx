import type { Metadata } from 'next'
import { KnowledgeGraphView } from '@/features/student/components/KnowledgeGraphView'

export const metadata: Metadata = { title: 'Knowledge Graph' }

export default function GraphPage() {
  return <KnowledgeGraphView />
}
