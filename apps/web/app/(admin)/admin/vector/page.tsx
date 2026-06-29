import type { Metadata } from 'next'
import { VectorStatsView } from '@/features/knowledge/components/VectorStatsView'

export const metadata: Metadata = { title: 'Vector Stats — Admin' }

export default function VectorPage() {
  return <VectorStatsView />
}
