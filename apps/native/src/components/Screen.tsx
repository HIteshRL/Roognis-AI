import { ReactNode } from 'react'
import { StyleSheet, View, ViewStyle } from 'react-native'
import { SafeAreaView, type Edge } from 'react-native-safe-area-context'
import { colors } from '@/theme/colors'

interface ScreenProps {
  children: ReactNode
  style?: ViewStyle
  edges?: Edge[]
  padded?: boolean
}

export function Screen({ children, style, edges = ['top'], padded = false }: ScreenProps) {
  return (
    <SafeAreaView style={styles.safe} edges={edges}>
      <View style={[styles.inner, padded && styles.padded, style]}>{children}</View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  inner: { flex: 1 },
  padded: { paddingHorizontal: 16 },
})
