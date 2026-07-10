import type { Metadata } from 'next'
import { RecommendationsView } from '@/features/student/components/RecommendationsView'

export const metadata: Metadata = { title: 'Recommendations' }

export default function RecommendationsPage() {
  return <RecommendationsView />
}
