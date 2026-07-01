import type { Metadata } from 'next'
import { MasteryDashboardView } from '@/features/student/components/MasteryDashboardView'

export const metadata: Metadata = { title: 'Mastery Dashboard' }

export default function MasteryPage() {
  return <MasteryDashboardView />
}
