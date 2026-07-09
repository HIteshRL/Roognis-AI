import { useRef } from 'react'
import {
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useChatStore } from '@/store/chat.store'
import { useChatStream } from '@/hooks/useChatStream'
import { Screen } from '@/components/Screen'
import { MessageBubble } from '@/components/MessageBubble'
import { ChatComposer } from '@/components/ChatComposer'
import { EmptyState } from '@/components/ui'
import type { MessageDto } from '@/types'
import { colors, radius, spacing } from '@/theme/colors'

export default function Chat() {
  const listRef = useRef<FlatList<MessageDto>>(null)
  const { send } = useChatStream()

  const messages = useChatStore((s) => s.messages)
  const streaming = useChatStore((s) => s.streaming)
  const pendingSubject = useChatStore((s) => s.pendingSubject)
  const pendingChapter = useChatStore((s) => s.pendingChapter)
  const activeConversationId = useChatStore((s) => s.activeConversationId)

  const isStreaming = streaming?.isStreaming ?? false
  const hasContext = !!pendingSubject || !!activeConversationId

  const streamingMessage: MessageDto | null = streaming
    ? {
        id: '__streaming__',
        conversation_id: activeConversationId ?? '',
        role: 'assistant',
        content: streaming.content,
        token_count: null,
        created_at: '',
      }
    : null

  const data = streamingMessage ? [...messages, streamingMessage] : messages

  const scrollToEnd = () => listRef.current?.scrollToEnd({ animated: true })

  const newChat = () => {
    useChatStore.getState().resetConversation()
    useChatStore.getState().setPendingChat(null, null)
  }

  return (
    <Screen>
      <View style={styles.header}>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>AI Tutor</Text>
          {pendingSubject ? (
            <Text style={styles.context} numberOfLines={1}>
              {[pendingSubject, pendingChapter].filter(Boolean).join(' · ')}
            </Text>
          ) : (
            <Text style={styles.context}>Ask anything from your syllabus</Text>
          )}
        </View>
        {(messages.length > 0 || hasContext) && (
          <Pressable style={styles.newBtn} onPress={newChat}>
            <Ionicons name="add" size={16} color={colors.text} />
            <Text style={styles.newText}>New</Text>
          </Pressable>
        )}
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 88 : 0}
      >
        {data.length === 0 ? (
          <EmptyState
            icon="chatbubbles-outline"
            title="Start learning"
            subtitle="Ask a question and your tutor will explain it — with an illustration to make it click."
          />
        ) : (
          <FlatList
            ref={listRef}
            data={data}
            keyExtractor={(m) => m.id}
            renderItem={({ item }) => <MessageBubble message={item} />}
            contentContainerStyle={styles.listContent}
            onContentSizeChange={scrollToEnd}
            keyboardDismissMode="interactive"
          />
        )}

        {isStreaming && !streaming?.content ? (
          <Text style={styles.typing}>Tutor is thinking…</Text>
        ) : null}

        <ChatComposer onSend={send} disabled={isStreaming} />
      </KeyboardAvoidingView>
    </Screen>
  )
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.cardBorder,
  },
  title: { color: colors.text, fontSize: 18, fontWeight: '700' },
  context: { color: colors.textMuted, fontSize: 13, marginTop: 1 },
  newBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.full,
    borderWidth: 1,
    borderColor: colors.cardBorder,
    backgroundColor: colors.card,
  },
  newText: { color: colors.text, fontSize: 13, fontWeight: '600' },
  listContent: { padding: spacing.lg, paddingBottom: spacing.sm },
  typing: {
    color: colors.textMuted,
    fontSize: 13,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.sm,
    fontStyle: 'italic',
  },
})
