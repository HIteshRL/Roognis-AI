import type { Metadata } from 'next'
import { TeacherClassesView } from '@/features/teacher/components/TeacherClassesView'

export const metadata: Metadata = { title: 'Classes' }

export default function TeacherPage() {
  return <TeacherClassesView />
}
