import { useState } from 'react'
import { useRouter } from 'expo-router'
import { useQuery } from '@tanstack/react-query'
import { Ionicons } from '@expo/vector-icons'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { chatApi } from '@/api/chat'
import { studentApi } from '@/api/student'
import { useChatStore } from '@/store/chat.store'
import { Screen } from '@/components/Screen'
import { EmptyState, Loading } from '@/components/ui'
import { colors, radius, spacing } from '@/theme/colors'

const ACCENTS = [colors.primary, colors.success, colors.accent, colors.warning, colors.danger]

export default function Subjects() {
  const router = useRouter()
  const [expanded, setExpanded] = useState<string | null>(null)

  const subjectsQ = useQuery({
    queryKey: ['subjects'],
    queryFn: () => chatApi.getSubjects().then((r) => r.data),
  })
  const profileQ = useQuery({
    queryKey: ['profile'],
    queryFn: () => studentApi.getProfile().then((r) => r.data),
  })

  // Merge subjects the student has used with the syllabus subjects on their profile.
  const names = Array.from(
    new Set([
      ...(profileQ.data?.subjects ?? []),
      ...(subjectsQ.data?.map((s) => s.subject).filter((s) => s !== 'General') ?? []),
    ]),
  )

  const openChat = (subject: string | null, chapter: string | null) => {
    useChatStore.getState().resetConversation()
    useChatStore.getState().setPendingChat(subject, chapter)
    router.push('/(tabs)/chat')
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.title}>Subjects</Text>
        <Text style={styles.sub}>Your school's syllabus — tap a chapter to learn it.</Text>
      </View>

      {subjectsQ.isLoading || profileQ.isLoading ? (
        <Loading label="Loading your subjects…" />
      ) : names.length === 0 ? (
        <EmptyState
          icon="library-outline"
          title="No subjects yet"
          subtitle="Your teacher hasn't assigned a syllabus, or you haven't started learning. Ask the tutor anything to begin."
        />
      ) : (
        <ScrollView contentContainerStyle={styles.list}>
          {names.map((subject, i) => (
            <SubjectRow
              key={subject}
              subject={subject}
              accent={ACCENTS[i % ACCENTS.length]}
              count={subjectsQ.data?.find((s) => s.subject === subject)?.count ?? 0}
              expanded={expanded === subject}
              onToggle={() => setExpanded(expanded === subject ? null : subject)}
              onStart={openChat}
            />
          ))}
        </ScrollView>
      )}
    </Screen>
  )
}

interface SubjectRowProps {
  subject: string
  accent: string
  count: number
  expanded: boolean
  onToggle: () => void
  onStart: (subject: string, chapter: string | null) => void
}

function SubjectRow({ subject, accent, count, expanded, onToggle, onStart }: SubjectRowProps) {
  const chaptersQ = useQuery({
    queryKey: ['chapters', subject],
    queryFn: () => chatApi.getChapters(subject).then((r) => r.data),
    enabled: expanded,
  })

  return (
    <View style={styles.card}>
      <Pressable style={styles.cardHead} onPress={onToggle}>
        <View style={[styles.dot, { backgroundColor: accent }]} />
        <Text style={styles.subjectName}>{subject}</Text>
        <Text style={styles.count}>{count}</Text>
        <Ionicons
          name={expanded ? 'chevron-up' : 'chevron-down'}
          size={18}
          color={colors.textFaint}
        />
      </Pressable>

      {expanded && (
        <View style={styles.body}>
          {chaptersQ.isLoading ? (
            <Text style={styles.muted}>Loading chapters…</Text>
          ) : (
            <>
              <View style={styles.chips}>
                {(chaptersQ.data ?? []).length === 0 ? (
                  <Text style={styles.muted}>No chapters recorded yet</Text>
                ) : (
                  chaptersQ.data!.map((ch) => (
                    <Pressable
                      key={ch.chapter}
                      style={styles.chip}
                      onPress={() => onStart(subject, ch.chapter)}
                    >
                      <Text style={styles.chipText}>{ch.chapter}</Text>
                    </Pressable>
                  ))
                )}
              </View>
              <Pressable style={styles.startBtn} onPress={() => onStart(subject, null)}>
                <Ionicons name="add" size={16} color={colors.primary} />
                <Text style={styles.startText}>New chat in {subject}</Text>
              </Pressable>
            </>
          )}
        </View>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  header: { paddingHorizontal: spacing.lg, paddingTop: spacing.sm, paddingBottom: spacing.md },
  title: { color: colors.text, fontSize: 26, fontWeight: '800' },
  sub: { color: colors.textMuted, fontSize: 14, marginTop: 2 },
  list: { padding: spacing.lg, paddingTop: 0, gap: spacing.sm },
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.cardBorder,
    marginBottom: spacing.sm,
    overflow: 'hidden',
  },
  cardHead: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    padding: spacing.lg,
  },
  dot: { width: 10, height: 10, borderRadius: 5 },
  subjectName: { flex: 1, color: colors.text, fontSize: 16, fontWeight: '600' },
  count: { color: colors.textFaint, fontSize: 13 },
  body: {
    borderTopWidth: 1,
    borderTopColor: colors.cardBorder,
    padding: spacing.lg,
    gap: spacing.md,
  },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.full,
    borderWidth: 1,
    borderColor: colors.cardBorder,
    backgroundColor: colors.bgElevated,
  },
  chipText: { color: colors.text, fontSize: 13 },
  muted: { color: colors.textMuted, fontSize: 13 },
  startBtn: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs },
  startText: { color: colors.primary, fontSize: 14, fontWeight: '600' },
})
