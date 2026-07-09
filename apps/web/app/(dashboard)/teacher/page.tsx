import type { Metadata } from 'next'
import { TeacherClassesView } from '@/features/school/components/TeacherClassesView'

export const metadata: Metadata = { title: 'Teacher Portal' }

export default function TeacherPage() {
  return <TeacherClassesView />
}
