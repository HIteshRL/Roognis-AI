import { useEffect } from 'react'
import { Stack, useRouter, useSegments } from 'expo-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { GestureHandlerRootView } from 'react-native-gesture-handler'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { StatusBar } from 'expo-status-bar'
import { useAuthStore } from '@/store/auth.store'
import { colors } from '@/theme/colors'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false } },
})

// Keeps the visible route in sync with auth state after the store hydrates.
function useAuthGate() {
  const token = useAuthStore((s) => s.token)
  const hasHydrated = useAuthStore((s) => s.hasHydrated)
  const segments = useSegments()
  const router = useRouter()

  useEffect(() => {
    if (!hasHydrated) return
    const inAuthGroup = segments[0] === '(auth)'
    if (!token && !inAuthGroup) {
      router.replace('/(auth)/sign-in')
    } else if (token && inAuthGroup) {
      router.replace('/(tabs)')
    }
  }, [token, hasHydrated, segments, router])
}

export default function RootLayout() {
  useAuthGate()

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <StatusBar style="light" />
          <Stack
            screenOptions={{
              headerShown: false,
              contentStyle: { backgroundColor: colors.bg },
              animation: 'fade',
            }}
          />
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  )
}
