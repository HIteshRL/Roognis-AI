import type { Metadata } from 'next'
import { WeakAreasView } from '@/features/student/components/WeakAreasView'

export const metadata: Metadata = { title: 'Weak Areas' }

export default function GapsPage() {
  return <WeakAreasView />
}
