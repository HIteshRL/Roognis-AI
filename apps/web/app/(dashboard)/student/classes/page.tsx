import type { Metadata } from 'next'
import { MyClassesView } from '@/features/student/components/MyClassesView'

export const metadata: Metadata = { title: 'My Classes' }

export default function StudentClassesPage() {
  return <MyClassesView />
}
