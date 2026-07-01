import type { Metadata } from 'next'
import { StatisticsView } from '@/features/student/components/StatisticsView'

export const metadata: Metadata = { title: 'Statistics' }

export default function StatisticsPage() {
  return <StatisticsView />
}
