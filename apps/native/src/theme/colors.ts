// Single source of truth for the mobile palette. Dark-first to match the
// web app's default classroom aesthetic.

export const colors = {
  bg: '#0B1120',
  bgElevated: '#111827',
  card: '#1F2937',
  cardBorder: '#2D3B4F',
  primary: '#6366F1',
  primaryMuted: 'rgba(99, 102, 241, 0.15)',
  accent: '#22D3EE',
  text: '#F9FAFB',
  textMuted: '#9CA3AF',
  textFaint: '#6B7280',
  success: '#34D399',
  successMuted: 'rgba(52, 211, 153, 0.15)',
  warning: '#FBBF24',
  danger: '#F87171',
  userBubble: '#6366F1',
  assistantBubble: '#1F2937',
} as const

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  full: 999,
} as const

export const masteryColor = (label: MasteryLabel): string => {
  switch (label) {
    case 'mastered':
      return colors.success
    case 'developing':
      return colors.accent
    case 'emerging':
      return colors.warning
    default:
      return colors.textFaint
  }
}

type MasteryLabel = 'mastered' | 'developing' | 'emerging' | 'not_started'
