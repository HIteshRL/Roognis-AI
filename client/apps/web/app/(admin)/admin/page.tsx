import type { Metadata } from 'next'
import { AdminOverview } from '@/features/knowledge/components/AdminOverview'

export const metadata: Metadata = { title: 'Admin — Roognis AI' }

export default function AdminPage() {
  return <AdminOverview />
}
