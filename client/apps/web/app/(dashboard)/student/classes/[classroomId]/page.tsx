import type { Metadata } from 'next'
import { StudentClassDetailView } from '@/features/student/components/StudentClassDetailView'

export const metadata: Metadata = { title: 'Class' }

export default async function StudentClassPage({
  params,
}: {
  params: Promise<{ classroomId: string }>
}) {
  const { classroomId } = await params
  return <StudentClassDetailView classroomId={classroomId} />
}
