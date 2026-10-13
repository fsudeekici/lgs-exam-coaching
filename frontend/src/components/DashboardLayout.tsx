import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import type { Role } from '../api'
import { useAuth } from '../auth/useAuth'

const ADMIN_NAV = [
  { to: '/admin', label: 'Denemeler' },
  { to: '/admin/students', label: 'Öğrenciler' },
  { to: '/admin/parents', label: 'Veliler' },
]

const ROLE_LABELS: Record<Role, string> = { admin: 'Yönetici', student: 'Öğrenci', parent: 'Veli' }

export default function DashboardLayout({ title, children }: { title: ReactNode; children?: ReactNode }) {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <Link to="/" className="font-semibold text-slate-900">
              LGS Koçluk
            </Link>
            {user?.role === 'admin' && (
              <nav className="flex gap-1 text-sm">
                {ADMIN_NAV.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/admin'}
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
            <span className="text-slate-600">
              {user?.full_name} {user && <span className="text-slate-400">({ROLE_LABELS[user.role]})</span>}
            </span>
            <button
              onClick={logout}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-slate-700 hover:bg-slate-100"
            >
              Çıkış yap
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8">
        <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
        <div className="mt-6">
          {children ?? (
            <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
              Henüz burada bir şey yok.
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
