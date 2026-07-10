import type { Metadata } from 'next'
import { SkillsView } from '@/features/student/components/SkillsView'

export const metadata: Metadata = { title: 'Skills & Competencies' }

export default function SkillsPage() {
  return <SkillsView />
}
