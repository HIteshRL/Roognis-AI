import type { Metadata } from 'next'
import { ClassroomChatView } from '@/features/chat/components/ClassroomChatView'

export const metadata: Metadata = { title: 'Chat' }

export default async function ConversationPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return <ClassroomChatView conversationId={id} />
}
