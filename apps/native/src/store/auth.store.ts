import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import { Platform } from 'react-native'
import * as SecureStore from 'expo-secure-store'
import type { UserDto } from '@/types'
import { setTokenGetter } from '@/api/client'

interface AuthState {
  user: UserDto | null
  token: string | null
  hasHydrated: boolean
  setAuth: (user: UserDto, token: string) => void
  clearAuth: () => void
  setHasHydrated: (v: boolean) => void
}

// SecureStore is an encrypted async store (Android Keystore) but has no web
// implementation, so fall back to localStorage when running in the browser
// (e.g. the `expo start --web` preview).
const nativeStorage = {
  getItem: (name: string) => SecureStore.getItemAsync(name),
  setItem: (name: string, value: string) => SecureStore.setItemAsync(name, value),
  removeItem: (name: string) => SecureStore.deleteItemAsync(name),
}

const webStorage = {
  getItem: async (name: string) =>
    typeof localStorage !== 'undefined' ? localStorage.getItem(name) : null,
  setItem: async (name: string, value: string) => {
    if (typeof localStorage !== 'undefined') localStorage.setItem(name, value)
  },
  removeItem: async (name: string) => {
    if (typeof localStorage !== 'undefined') localStorage.removeItem(name)
  },
}

const secureStorage = Platform.OS === 'web' ? webStorage : nativeStorage

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      hasHydrated: false,
      setAuth: (user, token) => set({ user, token }),
      clearAuth: () => set({ user: null, token: null }),
      setHasHydrated: (v) => set({ hasHydrated: v }),
    }),
    {
      name: 'roognis-auth',
      storage: createJSONStorage(() => secureStorage),
      partialize: (s) => ({ user: s.user, token: s.token }),
      onRehydrateStorage: () => (state) => state?.setHasHydrated(true),
    },
  ),
)

// Every API request reads the latest token straight from the store.
setTokenGetter(() => useAuthStore.getState().token)
