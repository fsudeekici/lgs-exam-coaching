import { Navigate, Outlet } from 'react-router-dom'
import type { Role } from '../api'
import { useAuth } from '../auth/useAuth'

/** Renders child routes only for a logged-in user with the given role. */
export default function ProtectedRoute({ role }: { role: Role }) {
  const { user, loading } = useAuth()

  if (loading) return <p className="p-8 text-slate-500">Loading…</p>
  if (!user) return <Navigate to="/login" replace />
  // Wrong role: send them to their own dashboard.
  if (user.role !== role) return <Navigate to={`/${user.role}`} replace />
  return <Outlet />
}
