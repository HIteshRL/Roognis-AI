import type { Metadata } from 'next'
import { SearchPlayground } from '@/features/search/components/SearchPlayground'

export const metadata: Metadata = { title: 'Search Playground — Admin' }

export default function SearchPage() {
  return <SearchPlayground />
}
