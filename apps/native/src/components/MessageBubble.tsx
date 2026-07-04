import { StyleSheet, Text, View } from 'react-native'
import Markdown from 'react-native-markdown-display'
import type { MessageDto } from '@/types'
import { colors, radius, spacing } from '@/theme/colors'

export function MessageBubble({ message }: { message: MessageDto }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <View style={[styles.row, styles.rowUser]}>
        <View style={[styles.bubble, styles.userBubble]}>
          <Text style={styles.userText}>{message.content}</Text>
        </View>
      </View>
    )
  }

  return (
    <View style={[styles.row, styles.rowAssistant]}>
      <View style={[styles.bubble, styles.assistantBubble]}>
        <Markdown style={markdownStyles as never}>{message.content || '…'}</Markdown>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  row: { width: '100%', marginBottom: spacing.md },
  rowUser: { alignItems: 'flex-end' },
  rowAssistant: { alignItems: 'flex-start' },
  bubble: {
    maxWidth: '88%',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radius.lg,
  },
  userBubble: { backgroundColor: colors.userBubble, borderBottomRightRadius: radius.sm },
  assistantBubble: {
    backgroundColor: colors.assistantBubble,
    borderWidth: 1,
    borderColor: colors.cardBorder,
    borderBottomLeftRadius: radius.sm,
  },
  userText: { color: '#FFFFFF', fontSize: 15, lineHeight: 21 },
})

const markdownStyles = {
  body: { color: colors.text, fontSize: 15, lineHeight: 22 },
  heading1: { color: colors.text, fontSize: 20, fontWeight: '700', marginTop: 8 },
  heading2: { color: colors.text, fontSize: 18, fontWeight: '700', marginTop: 8 },
  heading3: { color: colors.text, fontSize: 16, fontWeight: '700', marginTop: 6 },
  strong: { color: colors.text, fontWeight: '700' },
  bullet_list: { marginVertical: 4 },
  ordered_list: { marginVertical: 4 },
  code_inline: {
    backgroundColor: colors.bgElevated,
    color: colors.accent,
    borderRadius: 4,
    paddingHorizontal: 4,
  },
  code_block: {
    backgroundColor: colors.bgElevated,
    color: colors.text,
    borderRadius: radius.sm,
    padding: spacing.md,
  },
  fence: {
    backgroundColor: colors.bgElevated,
    color: colors.text,
    borderRadius: radius.sm,
    padding: spacing.md,
  },
  link: { color: colors.accent },
  blockquote: {
    backgroundColor: colors.bgElevated,
    borderColor: colors.primary,
    borderLeftWidth: 3,
    paddingHorizontal: spacing.md,
  },
} as const
