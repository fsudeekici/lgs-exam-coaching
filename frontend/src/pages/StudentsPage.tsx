import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  createStudent,
  errorMessage,
  fetchStudents,
  unblockStudentLogin,
  updateStudent,
  type Student,
  type StudentInput,
} from '../api'
import AccountFields, {
  inputClass,
  labelClass,
  LoginBlockedBadge,
  LoginBlockedNotice,
  StatusBadge,
} from '../components/AccountFields'
import DashboardLayout from '../components/DashboardLayout'
import { byName, daysAgo, formatDate } from '../format'

const EMPTY: StudentInput = { full_name: '', email: '', password: '', school: '', class_name: '', parent_consent_date: null }

export default function StudentsPage() {
  const [students, setStudents] = useState<Student[] | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<StudentInput>(EMPTY)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStudents()
      .then(setStudents)
      .catch((err) => setError(errorMessage(err)))
  }, [])

  const upsert = (saved: Student) =>
    setStudents((prev) => [...(prev ?? []).filter((s) => s.id !== saved.id), saved].sort(byName))

  const reset = () => {
    setEditingId(null)
    setForm(EMPTY)
  }

  const startEdit = (student: Student) => {
    setEditingId(student.id)
    setForm({
      full_name: student.full_name,
      email: student.email,
      password: '',
      school: student.school ?? '',
      class_name: student.class_name ?? '',
      parent_consent_date: student.parent_consent_date,
    })
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
        const saved = await createStudent(form)
        upsert(saved)
        setMessage(`${saved.full_name} eklendi.`)
      } else {
        // An empty password means "keep the current one".
        const { password, ...rest } = form
        const saved = await updateStudent(editingId, password ? form : rest)
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
      const saved = await unblockStudentLogin(id)
      upsert(saved)
      setMessage(`${saved.full_name} için giriş engeli kaldırıldı.`)
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const toggleActive = async (student: Student) => {
    if (
      student.is_active &&
      !window.confirm(`${student.full_name} pasifleştirilsin mi? Giriş yapamaz, deneme sonuçları silinmez.`)
    ) {
      return
    }
    setError(null)
    setMessage(null)
    try {
      upsert(await updateStudent(student.id, { is_active: !student.is_active }))
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const editing = students?.find((student) => student.id === editingId)
  const today = daysAgo(0)

  return (
    <DashboardLayout title="Öğrenciler">
      <form onSubmit={handleSubmit} className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-900">
          {editingId === null ? 'Yeni öğrenci' : 'Öğrenciyi düzenle'}
        </h2>
        <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <AccountFields
            value={form}
            onChange={(patch) => setForm((prev) => ({ ...prev, ...patch }))}
            editing={editingId !== null}
          />
          <label className={labelClass}>
            Okul
            <input
              maxLength={255}
              value={form.school}
              onChange={(e) => setForm({ ...form, school: e.target.value })}
              className={inputClass}
            />
          </label>
          <label className={labelClass}>
            Sınıf
            <input
              maxLength={50}
              placeholder="8-A"
              value={form.class_name}
              onChange={(e) => setForm({ ...form, class_name: e.target.value })}
              className={inputClass}
            />
          </label>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
          <label className="flex cursor-pointer items-center gap-2 text-sm font-medium text-slate-700">
            <input
              type="checkbox"
              checked={form.parent_consent_date !== null}
              onChange={(e) => setForm({ ...form, parent_consent_date: e.target.checked ? today : null })}
            />
            Veli onayı alındı
          </label>
          {form.parent_consent_date !== null ? (
            <input
              type="date"
              aria-label="Veli onay tarihi"
              required
              max={today}
              value={form.parent_consent_date}
              onChange={(e) => setForm({ ...form, parent_consent_date: e.target.value || today })}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-slate-900"
            />
          ) : (
            <span className="text-sm text-slate-500">Veli onayı işaretlenmeden öğrenci giriş yapamaz.</span>
          )}
        </div>
        {editing?.login_blocked && <LoginBlockedNotice onUnblock={() => unblock(editing.id)} />}
        <div className="mt-4 flex gap-3">
          <button
            type="submit"
            disabled={saving}
            className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {editingId === null ? 'Öğrenci ekle' : 'Kaydet'}
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
              <th className="px-4 py-2 font-medium">Okul</th>
              <th className="px-4 py-2 font-medium">Sınıf</th>
              <th className="px-4 py-2 font-medium">Veliler</th>
              <th className="px-4 py-2 font-medium">Veli onayı</th>
              <th className="px-4 py-2 font-medium">Durum</th>
              <th />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {students?.map((student) => (
              <tr key={student.id} className={student.is_active ? 'hover:bg-slate-50' : 'bg-slate-50 text-slate-400'}>
                <td className="px-4 py-2 font-medium">
                  <Link to={`/admin/students/${student.id}`} className="text-indigo-700 hover:underline">
                    {student.full_name}
                  </Link>
                </td>
                <td className="px-4 py-2">{student.email}</td>
                <td className="px-4 py-2">{student.school ?? '—'}</td>
                <td className="px-4 py-2">{student.class_name ?? '—'}</td>
                <td className="px-4 py-2">{student.parents.map((p) => p.full_name).join(', ') || '—'}</td>
                <td className="px-4 py-2 whitespace-nowrap">
                  {student.parent_consent_date ? (
                    formatDate(student.parent_consent_date)
                  ) : (
                    <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-900">
                      Bekleniyor · giriş kapalı
                    </span>
                  )}
                </td>
                <td className="px-4 py-2">
                  <StatusBadge active={student.is_active} />
                  {student.login_blocked && <LoginBlockedBadge />}
                </td>
                <td className="px-4 py-2 text-right whitespace-nowrap">
                  <button onClick={() => startEdit(student)} className="text-indigo-700 hover:underline">
                    Düzenle
                  </button>
                  <button
                    onClick={() => toggleActive(student)}
                    className={`ml-3 hover:underline ${student.is_active ? 'text-red-600' : 'text-green-700'}`}
                  >
                    {student.is_active ? 'Pasifleştir' : 'Etkinleştir'}
                  </button>
                </td>
              </tr>
            ))}
            {students?.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                  Henüz öğrenci yok.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </DashboardLayout>
  )
}
