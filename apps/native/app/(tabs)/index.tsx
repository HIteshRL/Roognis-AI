import { useRouter } from 'expo-router'
import { useQuery } from '@tanstack/react-query'
import { Ionicons } from '@expo/vector-icons'
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native'
import { studentApi } from '@/api/student'
import { useAuthStore } from '@/store/auth.store'
import { useChatStore } from '@/store/chat.store'
import { Screen } from '@/components/Screen'
import { StatCard } from '@/components/StatCard'
import { Card, Loading, SectionTitle } from '@/components/ui'
import { colors, radius, spacing } from '@/theme/colors'

export default function Home() {
  const router = useRouter()
  const user = useAuthStore((s) => s.user)

  const profileQ = useQuery({
    queryKey: ['profile'],
    queryFn: () => studentApi.getProfile().then((r) => r.data),
  })
  const analyticsQ = useQuery({
    queryKey: ['analytics'],
    queryFn: () => studentApi.getAnalytics().then((r) => r.data),
  })
  const recsQ = useQuery({
    queryKey: ['recommendations'],
    queryFn: () => studentApi.getRecommendations().then((r) => r.data),
  })

  const refreshing = profileQ.isRefetching || analyticsQ.isRefetching
  const refetchAll = () => {
    profileQ.refetch()
    analyticsQ.refetch()
    recsQ.refetch()
  }

  const startFreshChat = () => {
    useChatStore.getState().resetConversation()
    useChatStore.getState().setPendingChat(null, null)
    router.push('/(tabs)/chat')
  }

  const a = analyticsQ.data
  const signals = profileQ.data?.behavioral_signals

  return (
    <Screen>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={refetchAll} tintColor={colors.primary} />
        }
      >
        <Text style={styles.hello}>Hi, {user?.username ?? 'there'} 👋</Text>
        <Text style={styles.sub}>Here's where your learning stands today.</Text>

        <Pressable style={styles.cta} onPress={startFreshChat}>
          <View style={styles.ctaIcon}>
            <Ionicons name="sparkles" size={20} color="#FFFFFF" />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.ctaTitle}>Ask your tutor</Text>
            <Text style={styles.ctaSub}>Get an explanation with an illustration</Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color="#FFFFFF" />
        </Pressable>

        {profileQ.isLoading || analyticsQ.isLoading ? (
          <View style={{ height: 160 }}>
            <Loading label="Loading your progress…" />
          </View>
        ) : (
          <>
            <View style={styles.statRow}>
              <StatCard
                icon="trending-up"
                label="Avg mastery"
                value={a ? `${Math.round(a.average_mastery)}%` : '—'}
                tint={colors.success}
              />
              <StatCard
                icon="flame"
                label="Day streak"
                value={signals ? `${signals.engagement_streak}` : '—'}
                tint={colors.warning}
              />
            </View>
            <View style={styles.statRow}>
              <StatCard
                icon="checkmark-done"
                label="Mastered"
                value={a ? `${a.mastered_count}` : '—'}
                tint={colors.accent}
              />
              <StatCard
                icon="alert-circle"
                label="Active gaps"
                value={a ? `${a.active_gaps}` : '—'}
                tint={colors.danger}
              />
            </View>
          </>
        )}

        <View style={{ marginTop: spacing.xl }}>
          <SectionTitle>Recommended next</SectionTitle>
          {recsQ.isLoading ? (
            <Card>
              <Text style={styles.muted}>Finding your next best topic…</Text>
            </Card>
          ) : (recsQ.data?.length ?? 0) === 0 ? (
            <Card>
              <Text style={styles.muted}>
                No recommendations yet — start a conversation and we'll map your path.
              </Text>
            </Card>
          ) : (
            recsQ.data!.slice(0, 5).map((rec) => (
              <Pressable
                key={rec.concept_id}
                style={styles.recCard}
                onPress={() => {
                  useChatStore.getState().resetConversation()
                  useChatStore
                    .getState()
                    .setPendingChat(rec.subject ?? null, rec.chapter ?? null)
                  router.push('/(tabs)/chat')
                }}
              >
                <View style={styles.recIcon}>
                  <Ionicons name="bulb" size={16} color={colors.primary} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.recTitle} numberOfLines={1}>
                    {rec.concept_name}
                  </Text>
                  <Text style={styles.recReason} numberOfLines={1}>
                    {[rec.subject, rec.chapter].filter(Boolean).join(' · ') || rec.reason}
                  </Text>
                </View>
                <Ionicons name="chevron-forward" size={18} color={colors.textFaint} />
              </Pressable>
            ))
          )}
        </View>
      </ScrollView>
    </Screen>
  )
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, paddingBottom: spacing.xxl },
  hello: { color: colors.text, fontSize: 26, fontWeight: '800', marginTop: spacing.sm },
  sub: { color: colors.textMuted, fontSize: 14, marginTop: 2 },
  cta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    backgroundColor: colors.primary,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginTop: spacing.xl,
  },
  ctaIcon: {
    width: 40,
    height: 40,
    borderRadius: radius.md,
    backgroundColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaTitle: { color: '#FFFFFF', fontSize: 16, fontWeight: '700' },
  ctaSub: { color: 'rgba(255,255,255,0.85)', fontSize: 13, marginTop: 1 },
  statRow: { flexDirection: 'row', gap: spacing.md, marginTop: spacing.md },
  muted: { color: colors.textMuted, fontSize: 14 },
  recCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.cardBorder,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  recIcon: {
    width: 32,
    height: 32,
    borderRadius: radius.md,
    backgroundColor: colors.primaryMuted,
    alignItems: 'center',
    justifyContent: 'center',
  },
  recTitle: { color: colors.text, fontSize: 15, fontWeight: '600' },
  recReason: { color: colors.textMuted, fontSize: 12, marginTop: 1 },
})
