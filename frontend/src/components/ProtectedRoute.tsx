import { Navigate, Outlet } from 'react-router-dom'
import type { Role } from '../api'
import { useAuth } from '../auth/useAuth'
import ConsentPage from '../pages/ConsentPage'

/** Renders child routes only for a logged-in user; with `role`, only for that role. */
export default function ProtectedRoute({ role }: { role?: Role }) {
  const { user, loading } = useAuth()

  if (loading) return <p className="p-8 text-slate-500">Yükleniyor…</p>
  if (!user) return <Navigate to="/login" replace />
  // First login: nothing is shown until the privacy notice is accepted.
  if (!user.kvkk_consent_at) return <ConsentPage />
  // Wrong role: send them to their own dashboard.
  if (role && user.role !== role) return <Navigate to={`/${user.role}`} replace />
  return <Outlet />
}
