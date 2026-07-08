import type { Metadata } from 'next'
import { ParentPortalView } from '@/features/parent/components/ParentPortalView'

export const metadata: Metadata = { title: 'Parent Portal' }

export default function ParentPage() {
  return <ParentPortalView />
}
