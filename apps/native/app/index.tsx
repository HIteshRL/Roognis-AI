import { Redirect } from 'expo-router'
import { View } from 'react-native'
import { useAuthStore } from '@/store/auth.store'
import { Loading } from '@/components/ui'
import { colors } from '@/theme/colors'

export default function Index() {
  const token = useAuthStore((s) => s.token)
  const hasHydrated = useAuthStore((s) => s.hasHydrated)

  if (!hasHydrated) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg }}>
        <Loading label="Loading Roognis…" />
      </View>
    )
  }

  return <Redirect href={token ? '/(tabs)' : '/(auth)/sign-in'} />
}
