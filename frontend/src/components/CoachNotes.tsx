import { useEffect, useState, type FormEvent } from 'react'
import { addStudentNote, deleteNote, errorMessage, fetchStudentNotes, updateNote, type CoachNote } from '../api'
import { formatTimestamp } from '../format'

/** Admin's notes about one student, with a per-note switch for whether the parent sees it. */
export default function CoachNotes({ studentId }: { studentId: number }) {
  const [notes, setNotes] = useState<CoachNote[] | null>(null)
  const [body, setBody] = useState('')
  const [visible, setVisible] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStudentNotes(studentId)
      .then(setNotes)
      .catch((err) => setError(errorMessage(err)))
  }, [studentId])

  const run = async (action: () => Promise<void>) => {
    setError(null)
    try {
      await action()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    await run(async () => {
      const saved = await addStudentNote(studentId, { body, visible_to_parent: visible })
      setNotes((prev) => [saved, ...(prev ?? [])])
      setBody('')
      setVisible(false)
    })
    setSaving(false)
  }

  const toggleVisible = (note: CoachNote) =>
    run(async () => {
      const saved = await updateNote(note.id, { visible_to_parent: !note.visible_to_parent })
      setNotes((prev) => (prev ?? []).map((n) => (n.id === saved.id ? saved : n)))
    })

  const remove = (note: CoachNote) => {
    if (!window.confirm('Bu not silinsin mi?')) return
    return run(async () => {
      await deleteNote(note.id)
      setNotes((prev) => (prev ?? []).filter((n) => n.id !== note.id))
    })
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <form onSubmit={handleSubmit}>
        <textarea
          aria-label="Yeni not"
          required
          maxLength={2000}
          rows={3}
          placeholder="Yeni not yazın…"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
        />
        <div className="mt-2 flex flex-wrap items-center gap-4">
          <button
            type="submit"
            disabled={saving || body.trim() === ''}
            className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Not ekle
          </button>
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={visible} onChange={(e) => setVisible(e.target.checked)} />
            Veli görebilsin
          </label>
        </div>
      </form>

      {error && (
        <p role="alert" className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {notes && notes.length > 0 && (
        <ul className="mt-4 divide-y divide-slate-100 border-t border-slate-200">
          {notes.map((note) => (
            <li key={note.id} className="py-3">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                <span className="text-slate-500">{formatTimestamp(note.created_at)}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    note.visible_to_parent ? 'bg-green-50 text-green-800' : 'bg-slate-100 text-slate-700'
                  }`}
                >
                  {note.visible_to_parent ? 'Veli görür' : 'Sadece koç'}
                </span>
                <span className="ml-auto flex gap-3">
                  <button onClick={() => toggleVisible(note)} className="text-indigo-700 hover:underline">
                    {note.visible_to_parent ? 'Veliden gizle' : 'Veliye göster'}
                  </button>
                  <button onClick={() => remove(note)} className="text-red-600 hover:underline">
                    Sil
                  </button>
                </span>
              </div>
              <p className="mt-1 whitespace-pre-line text-slate-900">{note.body}</p>
            </li>
          ))}
        </ul>
      )}
      {notes?.length === 0 && <p className="mt-3 text-sm text-slate-500">Henüz not yok.</p>}
    </div>
  )
}
