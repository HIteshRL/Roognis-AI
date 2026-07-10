import Link from 'next/link'
import { BrainCircuit } from 'lucide-react'

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-12">
      <Link href="/" className="mb-8 flex items-center gap-2">
        <BrainCircuit className="h-7 w-7 text-primary" />
        <span className="text-xl font-semibold">Roognis AI</span>
      </Link>
      {children}
    </div>
  )
}
