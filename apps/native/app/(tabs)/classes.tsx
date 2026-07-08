import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Ionicons } from '@expo/vector-icons'
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import { schoolApi, type Classroom } from '@/api/school'
import { useAuthStore } from '@/store/auth.store'
import { Screen } from '@/components/Screen'
import { EmptyState, Loading } from '@/components/ui'
import { colors, radius, spacing } from '@/theme/colors'

export default function Classes() {
  const qc = useQueryClient()
  const role = useAuthStore((s) => s.user?.role ?? 'student')
  const isTeacher = role === 'teacher' || role === 'school_admin'
  const [code, setCode] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)

  const enrolledQ = useQuery({
    queryKey: ['enrolled'],
    queryFn: () => schoolApi.getEnrolled().then((r) => r.data),
  })

  const teachingQ = useQuery({
    queryKey: ['teaching'],
    queryFn: () => schoolApi.getMyClassrooms().then((r) => r.data),
    enabled: isTeacher,
  })

  const join = useMutation({
    mutationFn: () => schoolApi.joinClassroom(code.trim().toUpperCase()),
    onSuccess: () => {
      setCode('')
      qc.invalidateQueries({ queryKey: ['enrolled'] })
    },
  })

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.title}>Classes</Text>
        <Text style={styles.sub}>Join your school classrooms and follow the syllabus.</Text>
      </View>

      <ScrollView contentContainerStyle={styles.list}>
        {/* Join by code */}
        <View style={styles.joinRow}>
          <TextInput
            style={styles.input}
            placeholder="Enter join code"
            placeholderTextColor={colors.textFaint}
            autoCapitalize="characters"
            value={code}
            onChangeText={(t) => setCode(t.toUpperCase())}
            maxLength={16}
          />
          <Pressable
            style={[styles.joinBtn, (!code.trim() || join.isPending) && styles.btnDisabled]}
            disabled={!code.trim() || join.isPending}
            onPress={() => join.mutate()}
          >
            <Text style={styles.joinText}>Join</Text>
          </Pressable>
        </View>
        {join.isError && (
          <Text style={styles.error}>Couldn&apos;t join — check the code and try again.</Text>
        )}

        {/* Teaching (teachers only) */}
        {isTeacher && (
          <>
            <Text style={styles.groupTitle}>Teaching</Text>
            {teachingQ.isLoading ? (
              <Loading label="Loading…" />
            ) : (teachingQ.data ?? []).length === 0 ? (
              <Text style={styles.muted}>No classrooms yet. Create one on the web portal.</Text>
            ) : (
              teachingQ.data!.map((c) => (
                <View key={c.id} style={styles.card}>
                  <View style={styles.cardHead}>
                    <Ionicons name="school" size={18} color={colors.primary} />
                    <Text style={styles.name}>{c.name}</Text>
                    <View style={styles.codeBadge}>
                      <Text style={styles.codeText}>{c.join_code}</Text>
                    </View>
                  </View>
                  <Text style={styles.meta}>
                    {(c.subject ?? 'General')} · {c.student_count} students · {c.syllabus_count} chapters
                  </Text>
                </View>
              ))
            )}
          </>
        )}

        {/* Enrolled (student view) */}
        <Text style={styles.groupTitle}>Enrolled</Text>
        {enrolledQ.isLoading ? (
          <Loading label="Loading your classes…" />
        ) : (enrolledQ.data ?? []).length === 0 ? (
          <EmptyState
            icon="school-outline"
            title="No classes yet"
            subtitle="Ask your teacher for a join code and enter it above."
          />
        ) : (
          enrolledQ.data!.map((c) => (
            <ClassroomRow
              key={c.id}
              classroom={c}
              expanded={expanded === c.id}
              onToggle={() => setExpanded(expanded === c.id ? null : c.id)}
            />
          ))
        )}
      </ScrollView>
    </Screen>
  )
}

function ClassroomRow({
  classroom,
  expanded,
  onToggle,
}: {
  classroom: Classroom
  expanded: boolean
  onToggle: () => void
}) {
  const syllabusQ = useQuery({
    queryKey: ['student-syllabus', classroom.id],
    queryFn: () => schoolApi.getSyllabus(classroom.id).then((r) => r.data),
    enabled: expanded,
  })

  return (
    <View style={styles.card}>
      <Pressable style={styles.cardHead} onPress={onToggle}>
        <Ionicons name="library" size={18} color={colors.accent} />
        <View style={{ flex: 1 }}>
          <Text style={styles.name}>{classroom.name}</Text>
          <Text style={styles.meta}>
            {(classroom.subject ?? 'General')} · {classroom.syllabus_count} chapters
          </Text>
        </View>
        <Ionicons
          name={expanded ? 'chevron-up' : 'chevron-down'}
          size={18}
          color={colors.textFaint}
        />
      </Pressable>

      {expanded && (
        <View style={styles.body}>
          {syllabusQ.isLoading ? (
            <Text style={styles.muted}>Loading syllabus…</Text>
          ) : (syllabusQ.data ?? []).length === 0 ? (
            <Text style={styles.muted}>No published chapters yet.</Text>
          ) : (
            syllabusQ.data!.map((s) => (
              <View key={s.id} style={styles.syllabusItem}>
                <Ionicons name="book-outline" size={14} color={colors.primary} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.chapter}>{s.chapter}</Text>
                  {s.topic ? <Text style={styles.muted}>{s.topic}</Text> : null}
                </View>
                <Text style={styles.subjectTag}>{s.subject}</Text>
              </View>
            ))
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
  joinRow: { flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.sm },
  input: {
    flex: 1,
    backgroundColor: colors.card,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.cardBorder,
    color: colors.text,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    fontSize: 15,
    letterSpacing: 2,
  },
  joinBtn: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    paddingHorizontal: spacing.lg,
    justifyContent: 'center',
  },
  btnDisabled: { opacity: 0.5 },
  joinText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  error: { color: colors.danger, fontSize: 13, marginBottom: spacing.sm },
  groupTitle: {
    color: colors.textFaint,
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: spacing.md,
    marginBottom: spacing.xs,
  },
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.cardBorder,
    overflow: 'hidden',
  },
  cardHead: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, padding: spacing.lg },
  name: { flex: 1, color: colors.text, fontSize: 16, fontWeight: '600' },
  meta: { color: colors.textMuted, fontSize: 13, marginTop: 2 },
  codeBadge: {
    backgroundColor: colors.bgElevated,
    borderRadius: radius.full,
    paddingHorizontal: spacing.md,
    paddingVertical: 4,
    borderWidth: 1,
    borderColor: colors.cardBorder,
  },
  codeText: { color: colors.text, fontSize: 13, fontWeight: '700', letterSpacing: 1 },
  body: { borderTopWidth: 1, borderTopColor: colors.cardBorder, padding: spacing.lg, gap: spacing.sm },
  syllabusItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    backgroundColor: colors.bgElevated,
    borderRadius: radius.md,
    padding: spacing.md,
  },
  chapter: { color: colors.text, fontSize: 14, fontWeight: '600' },
  subjectTag: { color: colors.textFaint, fontSize: 11 },
  muted: { color: colors.textMuted, fontSize: 13 },
})
