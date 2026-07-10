import type { Metadata } from 'next'
import { UploadDashboard } from '@/features/upload/components/UploadDashboard'

export const metadata: Metadata = { title: 'Upload Documents — Admin' }

export default function UploadPage() {
  return <UploadDashboard />
}
