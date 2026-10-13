import { useState, type FormEvent } from 'react'
import { errorMessage } from '../api'
import { useAuth } from '../auth/useAuth'
import KvkkNotice from '../components/KvkkNotice'

/** Shown on first login: the user reads the privacy notice and accepts it before using the app. */
export default function ConsentPage() {
  const { user, logout, acceptPrivacyNotice } = useAuth()
  const [checked, setChecked] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await acceptPrivacyNotice()
    } catch (err) {
      setError(errorMessage(err))
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8">
      <main className="mx-auto max-w-2xl rounded-xl border border-slate-200 bg-white p-6 sm:p-8">
        <h1 className="text-2xl font-semibold text-slate-900">KVKK Aydınlatma Metni</h1>
        <p className="mt-1 text-sm text-slate-600">
          Merhaba {user?.full_name}. Devam etmeden önce lütfen aşağıdaki metni okuyup onaylayın.
        </p>

        <div
          tabIndex={0}
          aria-label="KVKK Aydınlatma Metni"
          className="mt-4 max-h-[50vh] overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-4"
        >
          <KvkkNotice />
        </div>

        <form onSubmit={handleSubmit} className="mt-4">
          <label className="flex cursor-pointer items-start gap-3 text-sm text-slate-900">
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              className="mt-0.5 h-5 w-5 shrink-0"
            />
            <span>
              KVKK Aydınlatma Metni’ni okudum, anladım; kişisel verilerimin bu metinde belirtilen amaçlarla işlenmesini
              kabul ediyorum.
            </span>
          </label>

          {error && (
            <p role="alert" className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={!checked || saving}
              className="min-h-11 rounded-md bg-indigo-600 px-5 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              Onaylıyorum ve devam et
            </button>
            <button
              type="button"
              onClick={logout}
              className="min-h-11 rounded-md border border-slate-300 px-5 text-slate-700 hover:bg-slate-100"
            >
              Çıkış yap
            </button>
          </div>
        </form>
      </main>
    </div>
  )
}
