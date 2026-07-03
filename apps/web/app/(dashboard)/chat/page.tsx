import type { Metadata } from 'next'
import { ClassroomChatView } from '@/features/chat/components/ClassroomChatView'

export const metadata: Metadata = { title: 'Chat' }

export default function ChatPage() {
  return <ClassroomChatView />
}
