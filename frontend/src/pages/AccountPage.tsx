import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { changePassword, errorMessage } from '../api'
import { useAuth } from '../auth/useAuth'
import DashboardLayout from '../components/DashboardLayout'
import { formatTimestamp } from '../format'

const inputClass =
  'mt-1 h-11 w-full rounded-md border border-slate-300 px-3 text-base text-slate-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none'

/** The logged-in user's own account: details and password change. */
export default function AccountPage() {
  const { user } = useAuth()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [repeat, setRepeat] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setMessage(null)
    if (next !== repeat) {
      setError('Yeni şifreler birbiriyle aynı değil.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await changePassword(current, next)
      setMessage('Şifreniz değiştirildi. Diğer cihazlardaki oturumlar kapatıldı.')
      setCurrent('')
      setNext('')
      setRepeat('')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <DashboardLayout title="Hesabım" narrow>
      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
        <div className="font-medium text-slate-900">{user?.full_name}</div>
        <div className="text-slate-600">{user?.email}</div>
        {user?.kvkk_consent_at && (
          <div className="mt-2 text-slate-500">
            <Link to="/kvkk" className="text-indigo-700 hover:underline">
              KVKK Aydınlatma Metni
            </Link>{' '}
            onay tarihi: {formatTimestamp(user.kvkk_consent_at)}
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-900">Şifre değiştir</h2>
        <label className="mt-3 block text-sm font-medium text-slate-700">
          Mevcut şifre
          <input
            type="password"
            required
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            className={inputClass}
          />
        </label>
        <label className="mt-3 block text-sm font-medium text-slate-700">
          Yeni şifre
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            placeholder="En az 8 karakter"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            className={inputClass}
          />
        </label>
        <label className="mt-3 block text-sm font-medium text-slate-700">
          Yeni şifre (tekrar)
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={repeat}
            onChange={(e) => setRepeat(e.target.value)}
            className={inputClass}
          />
        </label>

        {message && (
          <p role="status" className="mt-3 rounded-md bg-green-50 px-3 py-2 text-sm text-green-800">
            {message}
          </p>
        )}
        {error && (
          <p role="alert" className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={saving}
          className="mt-4 h-11 rounded-md bg-indigo-600 px-5 font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
        >
          {saving ? 'Kaydediliyor…' : 'Şifreyi değiştir'}
        </button>
      </form>
    </DashboardLayout>
  )
}
