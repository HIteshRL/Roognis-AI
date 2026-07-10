import type { Metadata } from 'next'
import { ChatView } from '@/features/chat/components/ChatView'

export const metadata: Metadata = { title: 'Chat' }

export default function ConversationPage({ params }: { params: { id: string } }) {
  return <ChatView conversationId={params.id} />
}
