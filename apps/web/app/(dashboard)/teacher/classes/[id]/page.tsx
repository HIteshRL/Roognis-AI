import type { Metadata } from 'next'
import { ClassroomDetailView } from '@/features/school/components/ClassroomDetailView'

export const metadata: Metadata = { title: 'Classroom' }

export default async function ClassroomPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return <ClassroomDetailView classroomId={id} />
}
