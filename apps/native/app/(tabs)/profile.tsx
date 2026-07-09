import { useRouter } from 'expo-router'
import { useQuery } from '@tanstack/react-query'
import { Ionicons } from '@expo/vector-icons'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { studentApi } from '@/api/student'
import { useAuthStore } from '@/store/auth.store'
import { useChatStore } from '@/store/chat.store'
import { Screen } from '@/components/Screen'
import { Card, Loading, SectionTitle } from '@/components/ui'
import { colors, radius, spacing } from '@/theme/colors'

export default function Profile() {
  const router = useRouter()
  const user = useAuthStore((s) => s.user)
  const clearAuth = useAuthStore((s) => s.clearAuth)

  const profileQ = useQuery({
    queryKey: ['profile'],
    queryFn: () => studentApi.getProfile().then((r) => r.data),
  })

  const logout = () => {
    useChatStore.getState().resetConversation()
    clearAuth()
    router.replace('/(auth)/sign-in')
  }

  const p = profileQ.data
  const s = p?.behavioral_signals

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.identity}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {(user?.username ?? 'U').slice(0, 1).toUpperCase()}
            </Text>
          </View>
          <Text style={styles.name}>{user?.username ?? 'Student'}</Text>
          <Text style={styles.email}>{user?.email}</Text>
        </View>

        {profileQ.isLoading ? (
          <View style={{ height: 120 }}>
            <Loading />
          </View>
        ) : (
          <>
            <SectionTitle>Learner profile</SectionTitle>
            <Card style={styles.card}>
              <Row label="Institution" value={p?.institution ?? 'Not set'} />
              <Row label="Grade" value={p?.grade ?? 'Not set'} />
              <Row label="Current chapter" value={p?.current_chapter ?? 'Not set'} />
              <Row
                label="Subjects"
                value={p?.subjects?.length ? p.subjects.join(', ') : 'None yet'}
              />
            </Card>

            <SectionTitle>Learning style</SectionTitle>
            <Card style={styles.card}>
              <Row label="Response pattern" value={s?.response_pattern ?? 'unknown'} />
              <Row label="Dominant subject" value={s?.dominant_subject ?? '—'} />
              <Row label="Total sessions" value={`${s?.total_sessions ?? 0}`} />
              <Row label="Engagement streak" value={`${s?.engagement_streak ?? 0} days`} />
              {s?.strengths?.length ? (
                <Row label="Strengths" value={s.strengths.slice(0, 4).join(', ')} />
              ) : null}
            </Card>
          </>
        )}

        <Pressable style={styles.logout} onPress={logout}>
          <Ionicons name="log-out-outline" size={18} color={colors.danger} />
          <Text style={styles.logoutText}>Sign out</Text>
        </Pressable>

        <Text style={styles.version}>Roognis · v0.1.0</Text>
      </ScrollView>
    </Screen>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue} numberOfLines={1}>
        {value}
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, paddingBottom: spacing.xxl },
  identity: { alignItems: 'center', gap: 2, marginVertical: spacing.lg },
  avatar: {
    width: 72,
    height: 72,
    borderRadius: radius.full,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  avatarText: { color: '#FFFFFF', fontSize: 30, fontWeight: '800' },
  name: { color: colors.text, fontSize: 20, fontWeight: '700' },
  email: { color: colors.textMuted, fontSize: 14 },
  card: { gap: spacing.sm, marginBottom: spacing.lg },
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.md },
  rowLabel: { color: colors.textMuted, fontSize: 14 },
  rowValue: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '500',
    flexShrink: 1,
    textAlign: 'right',
    textTransform: 'capitalize',
  },
  logout: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.danger,
    borderRadius: radius.md,
    paddingVertical: spacing.lg,
    marginTop: spacing.md,
  },
  logoutText: { color: colors.danger, fontSize: 15, fontWeight: '600' },
  version: {
    color: colors.textFaint,
    fontSize: 12,
    textAlign: 'center',
    marginTop: spacing.xl,
  },
})
