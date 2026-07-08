import type { Metadata } from 'next'
import { GuardiansView } from '@/features/student/components/GuardiansView'

export const metadata: Metadata = { title: 'Family Access' }

export default function GuardiansPage() {
  return <GuardiansView />
}
