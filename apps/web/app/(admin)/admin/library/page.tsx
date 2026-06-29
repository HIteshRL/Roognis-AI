import type { Metadata } from 'next'
import { KnowledgeLibraryView } from '@/features/knowledge/components/KnowledgeLibraryView'

export const metadata: Metadata = { title: 'Knowledge Library — Admin' }

export default function LibraryPage() {
  return <KnowledgeLibraryView />
}
