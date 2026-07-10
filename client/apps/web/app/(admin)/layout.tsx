import { redirect } from 'next/navigation'
import { auth } from '@clerk/nextjs/server'
import { AdminSidebar } from '@/components/layout/AdminSidebar'

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const { userId } = await auth()
  if (!userId) redirect('/login')
  // Admin role check happens at the API level — UI shows the panel for authenticated users,
  // any admin-only API calls will return 403 if they lack the role.
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <AdminSidebar />
      <main className="flex flex-1 flex-col overflow-hidden">{children}</main>
    </div>
  )
}
