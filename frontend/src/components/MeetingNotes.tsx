import { useState, type FormEvent } from 'react'
import { addMeetingNote, deleteMeetingNote, errorMessage, type MeetingNote } from '../api'
import { daysAgo, formatDate } from '../format'

interface Props {
  studentId: number
  /** Latest meeting first. */
  initialNotes: MeetingNote[]
}

/** Notes the coach writes after each parent meeting. The form and delete buttons are left out of the printout. */
export default function MeetingNotes({ studentId, initialNotes }: Props) {
  const [notes, setNotes] = useState(initialNotes)
  const [meetingDate, setMeetingDate] = useState(() => daysAgo(0))
  const [body, setBody] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setSaving(true)
    try {
      const saved = await addMeetingNote(studentId, { meeting_date: meetingDate, body })
      setNotes((prev) =>
        [saved, ...prev].sort((a, b) => b.meeting_date.localeCompare(a.meeting_date) || b.id - a.id),
      )
      setBody('')
    } catch (err) {
      setError(errorMessage(err))
    }
    setSaving(false)
  }

  const remove = async (note: MeetingNote) => {
    if (!window.confirm('Bu görüşme notu silinsin mi?')) return
    setError(null)
    try {
      await deleteMeetingNote(note.id)
      setNotes((prev) => prev.filter((n) => n.id !== note.id))
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <form onSubmit={handleSubmit} className="mb-4 border-b border-slate-200 pb-4 print:hidden">
        <label className="block text-sm font-medium text-slate-700">
          Görüşme tarihi
          <input
            type="date"
            required
            max={daysAgo(0)}
            value={meetingDate}
            onChange={(e) => setMeetingDate(e.target.value)}
            className="mt-1 block rounded-md border border-slate-300 px-3 py-2 text-slate-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
          />
        </label>
        <textarea
          aria-label="Görüşme notu"
          required
          maxLength={4000}
          rows={3}
          placeholder="Görüşmede konuşulanlar, alınan kararlar…"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          className="mt-3 w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={saving || body.trim() === ''}
          className="mt-2 rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          Görüşme notu ekle
        </button>
      </form>

      {error && (
        <p role="alert" className="mb-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {notes.length === 0 ? (
        <p className="text-sm text-slate-500">Henüz görüşme notu yok.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {notes.map((note) => (
            <li key={note.id} className="break-inside-avoid py-3 first:pt-0 last:pb-0">
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="font-semibold text-slate-900">{formatDate(note.meeting_date)}</span>
                <button onClick={() => remove(note)} className="text-red-600 hover:underline print:hidden">
                  Sil
                </button>
              </div>
              <p className="mt-1 whitespace-pre-line text-slate-900">{note.body}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
