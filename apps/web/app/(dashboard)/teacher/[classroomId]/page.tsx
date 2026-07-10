import type { Metadata } from 'next'
import { ClassroomDetailView } from '@/features/teacher/components/ClassroomDetailView'

export const metadata: Metadata = { title: 'Class' }

export default async function ClassroomPage({
  params,
}: {
  params: Promise<{ classroomId: string }>
}) {
  const { classroomId } = await params
  return <ClassroomDetailView classroomId={classroomId} />
}
