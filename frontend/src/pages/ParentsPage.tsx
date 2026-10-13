import { useEffect, useState, type FormEvent } from 'react'
import {
  createParent,
  errorMessage,
  fetchParents,
  fetchStudents,
  unblockParentLogin,
  updateParent,
  type Parent,
  type ParentInput,
  type Student,
} from '../api'
import AccountFields, { LoginBlockedBadge, LoginBlockedNotice, StatusBadge } from '../components/AccountFields'
import DashboardLayout from '../components/DashboardLayout'
import { byName } from '../format'

const EMPTY: ParentInput = { full_name: '', email: '', password: '', student_ids: [] }

export default function ParentsPage() {
  const [parents, setParents] = useState<Parent[] | null>(null)
  const [students, setStudents] = useState<Student[]>([])
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<ParentInput>(EMPTY)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchParents(), fetchStudents()])
      .then(([parentData, studentData]) => {
        setParents(parentData)
        setStudents(studentData)
      })
      .catch((err) => setError(errorMessage(err)))
  }, [])

  const upsert = (saved: Parent) =>
    setParents((prev) => [...(prev ?? []).filter((p) => p.id !== saved.id), saved].sort(byName))

  const reset = () => {
    setEditingId(null)
    setForm(EMPTY)
  }

  const startEdit = (parent: Parent) => {
    setEditingId(parent.id)
    setForm({
      full_name: parent.full_name,
      email: parent.email,
      password: '',
      student_ids: parent.students.map((s) => s.id),
    })
    setMessage(null)
    setError(null)
    window.scrollTo({ top: 0 })
  }

  const toggleStudent = (id: number) =>
    setForm((prev) => ({
      ...prev,
      student_ids: prev.student_ids.includes(id)
        ? prev.student_ids.filter((studentId) => studentId !== id)
        : [...prev.student_ids, id],
    }))

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      if (editingId === null) {
        const saved = await createParent(form)
        upsert(saved)
        setMessage(`${saved.full_name} eklendi.`)
      } else {
        // An empty password means "keep the current one".
        const { password, ...rest } = form
        const saved = await updateParent(editingId, password ? form : rest)
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
      const saved = await unblockParentLogin(id)
      upsert(saved)
      setMessage(`${saved.full_name} için giriş engeli kaldırıldı.`)
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const toggleActive = async (parent: Parent) => {
    if (parent.is_active && !window.confirm(`${parent.full_name} pasifleştirilsin mi? Giriş yapamaz.`)) return
    setError(null)
    setMessage(null)
    try {
      upsert(await updateParent(parent.id, { is_active: !parent.is_active }))
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  // Offer active students, plus any deactivated one that is already linked.
  const editing = parents?.find((parent) => parent.id === editingId)
  const selectable = students.filter((s) => s.is_active || form.student_ids.includes(s.id))

  return (
    <DashboardLayout title="Veliler">
      <form onSubmit={handleSubmit} className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-900">{editingId === null ? 'Yeni veli' : 'Veliyi düzenle'}</h2>
        <div className="mt-3 grid gap-4 sm:grid-cols-3">
          <AccountFields
            value={form}
            onChange={(patch) => setForm((prev) => ({ ...prev, ...patch }))}
            editing={editingId !== null}
          />
        </div>

        <fieldset className="mt-4">
          <legend className="text-sm font-medium text-slate-700">Öğrencileri</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {selectable.map((student) => (
              <label
                key={student.id}
                className="flex cursor-pointer items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 has-checked:border-indigo-500 has-checked:bg-indigo-50 has-checked:text-indigo-800"
              >
                <input
                  type="checkbox"
                  checked={form.student_ids.includes(student.id)}
                  onChange={() => toggleStudent(student.id)}
                />
                {student.full_name}
                {student.class_name && <span className="text-slate-400">({student.class_name})</span>}
              </label>
            ))}
            {selectable.length === 0 && <span className="text-sm text-slate-500">Önce öğrenci ekleyin.</span>}
          </div>
        </fieldset>

        {editing?.login_blocked && <LoginBlockedNotice onUnblock={() => unblock(editing.id)} />}

        <div className="mt-4 flex gap-3">
          <button
            type="submit"
            disabled={saving}
            className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {editingId === null ? 'Veli ekle' : 'Kaydet'}
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
              <th className="px-4 py-2 font-medium">Öğrencileri</th>
              <th className="px-4 py-2 font-medium">Durum</th>
              <th />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {parents?.map((parent) => (
              <tr key={parent.id} className={parent.is_active ? 'hover:bg-slate-50' : 'bg-slate-50 text-slate-400'}>
                <td className="px-4 py-2 font-medium">{parent.full_name}</td>
                <td className="px-4 py-2">{parent.email}</td>
                <td className="px-4 py-2">{parent.students.map((s) => s.full_name).join(', ') || '—'}</td>
                <td className="px-4 py-2">
                  <StatusBadge active={parent.is_active} />
                  {parent.login_blocked && <LoginBlockedBadge />}
                </td>
                <td className="px-4 py-2 text-right whitespace-nowrap">
                  <button onClick={() => startEdit(parent)} className="text-indigo-700 hover:underline">
                    Düzenle
                  </button>
                  <button
                    onClick={() => toggleActive(parent)}
                    className={`ml-3 hover:underline ${parent.is_active ? 'text-red-600' : 'text-green-700'}`}
                  >
                    {parent.is_active ? 'Pasifleştir' : 'Etkinleştir'}
                  </button>
                </td>
              </tr>
            ))}
            {parents?.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                  Henüz veli yok.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </DashboardLayout>
  )
}
