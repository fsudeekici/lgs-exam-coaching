import { useEffect, useState, type FormEvent } from 'react'
import {
  createAdmin,
  errorMessage,
  fetchAdmins,
  unblockAdminLogin,
  updateAdmin,
  type Admin,
  type AdminInput,
} from '../api'
import { useAuth } from '../auth/useAuth'
import AccountFields, { LoginBlockedBadge, LoginBlockedNotice, StatusBadge } from '../components/AccountFields'
import DashboardLayout from '../components/DashboardLayout'
import { byName } from '../format'

const EMPTY: AdminInput = { full_name: '', email: '', password: '' }

/** Main admin only: the other admins (coaches). Each coach sees only the students assigned to them. */
export default function AdminsPage() {
  const { user } = useAuth()
  const [admins, setAdmins] = useState<Admin[] | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<AdminInput>(EMPTY)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAdmins()
      .then(setAdmins)
      .catch((err) => setError(errorMessage(err)))
  }, [])

  const upsert = (saved: Admin) =>
    setAdmins((prev) => [...(prev ?? []).filter((a) => a.id !== saved.id), saved].sort(byName))

  const reset = () => {
    setEditingId(null)
    setForm(EMPTY)
  }

  const startEdit = (admin: Admin) => {
    setEditingId(admin.id)
    setForm({ full_name: admin.full_name, email: admin.email, password: '' })
    setMessage(null)
    setError(null)
    window.scrollTo({ top: 0 })
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      if (editingId === null) {
        const saved = await createAdmin(form)
        upsert(saved)
        setMessage(`${saved.full_name} eklendi. Kendi öğrencilerini ve velilerini kendisi ekleyebilir.`)
      } else {
        // An empty password means "keep the current one".
        const { password, ...rest } = form
        const saved = await updateAdmin(editingId, password ? form : rest)
        upsert(saved)
        setMessage(`${saved.full_name} güncellendi.`)
      }
      reset()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const unblock = async (id: number) => {
    setError(null)
    setMessage(null)
    try {
      const saved = await unblockAdminLogin(id)
      upsert(saved)
      setMessage(`${saved.full_name} için giriş engeli kaldırıldı.`)
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const toggleActive = async (admin: Admin) => {
    if (
      admin.is_active &&
      !window.confirm(`${admin.full_name} pasifleştirilsin mi? Giriş yapamaz, öğrencileri ve verileri silinmez.`)
    ) {
      return
    }
    setError(null)
    setMessage(null)
    try {
      upsert(await updateAdmin(admin.id, { is_active: !admin.is_active }))
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const editing = admins?.find((admin) => admin.id === editingId)

  return (
    <DashboardLayout title="Yöneticiler">
      <form onSubmit={handleSubmit} className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-900">
          {editingId === null ? 'Yeni yönetici' : 'Yöneticiyi düzenle'}
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Her yönetici yalnızca kendi eklediği öğrencileri ve velileri görür.
        </p>
        <div className="mt-3 grid gap-4 sm:grid-cols-3">
          <AccountFields
            value={form}
            onChange={(patch) => setForm((prev) => ({ ...prev, ...patch }))}
            editing={editingId !== null}
          />
        </div>

        {editing?.login_blocked && <LoginBlockedNotice onUnblock={() => unblock(editing.id)} />}

        <div className="mt-4 flex gap-3">
          <button
            type="submit"
            disabled={saving}
            className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {editingId === null ? 'Yönetici ekle' : 'Kaydet'}
          </button>
          {editingId !== null && (
            <button
              type="button"
              onClick={reset}
              className="rounded-md border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-100"
            >
              Vazgeç
            </button>
          )}
        </div>
      </form>

      {message && (
        <p role="status" className="mt-4 rounded-md bg-green-50 px-3 py-2 text-sm text-green-800">
          {message}
        </p>
      )}
      {error && (
        <p role="alert" className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="mt-6 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
            <tr>
              <th className="px-4 py-2 font-medium">Ad soyad</th>
              <th className="px-4 py-2 font-medium">E-posta</th>
              <th className="px-4 py-2 font-medium">Aktif öğrenci</th>
              <th className="px-4 py-2 font-medium">Durum</th>
              <th />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {admins?.map((admin) => (
              <tr key={admin.id} className={admin.is_active ? 'hover:bg-slate-50' : 'bg-slate-50 text-slate-400'}>
                <td className="px-4 py-2 font-medium">
                  {admin.full_name}
                  {admin.is_superadmin && (
                    <span className="ml-2 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-800">
                      Ana yönetici
                    </span>
                  )}
                </td>
                <td className="px-4 py-2">{admin.email}</td>
                <td className="px-4 py-2">{admin.student_count}</td>
                <td className="px-4 py-2">
                  <StatusBadge active={admin.is_active} />
                  {admin.login_blocked && <LoginBlockedBadge />}
                </td>
                <td className="px-4 py-2 text-right whitespace-nowrap">
                  <button onClick={() => startEdit(admin)} className="text-indigo-700 hover:underline">
                    Düzenle
                  </button>
                  {admin.id !== user?.id && (
                    <button
                      onClick={() => toggleActive(admin)}
                      className={`ml-3 hover:underline ${admin.is_active ? 'text-red-600' : 'text-green-700'}`}
                    >
                      {admin.is_active ? 'Pasifleştir' : 'Etkinleştir'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DashboardLayout>
  )
}
