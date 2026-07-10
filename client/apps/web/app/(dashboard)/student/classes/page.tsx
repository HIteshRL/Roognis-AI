import type { Metadata } from 'next'
import { StudentClassesView } from '@/features/student/components/StudentClassesView'

export const metadata: Metadata = { title: 'My Classes' }

export default function StudentClassesPage() {
  return <StudentClassesView />
}
