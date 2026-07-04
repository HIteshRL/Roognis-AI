import { AdminSidebar } from '@/components/layout/AdminSidebar'
import { AuthGuard } from '@/components/layout/AuthGuard'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  // Admin role check happens at the API level — UI shows the panel for authenticated users,
  // any admin-only API calls will return 403 if they lack the role.
  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden bg-background">
        <AdminSidebar />
        <main className="flex flex-1 flex-col overflow-hidden">{children}</main>
      </div>
    </AuthGuard>
  )
}
