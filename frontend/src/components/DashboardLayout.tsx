import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import type { Role } from '../api'
import { useAuth } from '../auth/useAuth'

const ADMIN_NAV = [
  { to: '/admin', label: 'Denemeler' },
  { to: '/admin/students', label: 'Öğrenciler' },
  { to: '/admin/parents', label: 'Veliler' },
]

const STUDENT_NAV = [
  { to: '/student', label: 'Soru takibi' },
  { to: '/student/topics', label: 'Konular' },
  { to: '/student/analytics', label: 'Denemeler' },
]

const NAV: Record<Role, { to: string; label: string }[]> = { admin: ADMIN_NAV, student: STUDENT_NAV, parent: [] }

const ROLE_LABELS: Record<Role, string> = { admin: 'Yönetici', student: 'Öğrenci', parent: 'Veli' }

interface Props {
  title: ReactNode
  children?: ReactNode
  /** Phone-width column, for pages that are mostly a form or a list. */
  narrow?: boolean
}

export default function DashboardLayout({ title, children, narrow }: Props) {
  const { user, logout } = useAuth()
  const nav = user ? NAV[user.role] : []
  // Students mostly use a phone: their navigation is a bar at the bottom of the screen there.
  const bottomNav = user?.role === 'student'

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <Link to="/" className="font-semibold text-slate-900">
              LGS Koçluk
            </Link>
            {nav.length > 0 && (
              <nav className={`gap-1 text-sm ${bottomNav ? 'hidden sm:flex' : 'flex'}`}>
                {nav.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/admin' || item.to === '/student'}
                    className={({ isActive }) =>
                      `rounded-md px-3 py-1.5 ${isActive ? 'bg-indigo-50 font-medium text-indigo-700' : 'text-slate-600 hover:bg-slate-100'}`
                    }
                  >
                    {item.label}
                  </NavLink>
                ))}
              </nav>
            )}
          </div>
          <div className="flex items-center gap-4 text-sm">
            <Link to="/account" className="text-slate-600 hover:text-indigo-700 hover:underline" title="Hesabım">
              {user?.full_name} {user && <span className="text-slate-400">({ROLE_LABELS[user.role]})</span>}
            </Link>
            <button
              onClick={logout}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-slate-700 hover:bg-slate-100"
            >
              Çıkış yap
            </button>
          </div>
        </div>
      </header>
      <main className={`mx-auto px-4 py-6 sm:py-8 ${narrow ? 'max-w-xl' : 'max-w-7xl'} ${bottomNav ? 'pb-24 sm:pb-8' : ''}`}>
        <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
        <div className="mt-6">
          {children ?? (
            <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
              Henüz burada bir şey yok.
            </div>
          )}
        </div>
        <footer className="mt-10 text-center text-xs text-slate-400">
          <Link to="/kvkk" className="hover:text-slate-600 hover:underline">
            KVKK Aydınlatma Metni
          </Link>
        </footer>
      </main>
      {bottomNav && (
        <nav className="fixed inset-x-0 bottom-0 z-10 flex border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] sm:hidden">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/student'}
              className={({ isActive }) =>
                `flex min-h-14 flex-1 items-center justify-center border-t-2 px-1 text-center text-sm ${
                  isActive ? 'border-indigo-600 font-semibold text-indigo-700' : 'border-transparent text-slate-600'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  )
}
