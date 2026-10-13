import { useEffect, useRef, useState, type FormEvent } from 'react'
import { addQuestionLog, deleteQuestionLog, errorMessage, fetchMyQuestionLogs, fetchMySubjects, type QuestionLog, type Subject } from '../api'
import DashboardLayout from '../components/DashboardLayout'
import { LogTotals, QuestionLogList } from '../components/study'
import { daysAgo } from '../format'

// 16px text keeps iOS from zooming in when an input is focused.
const numberClass =
  'mt-1 h-12 w-full rounded-md border border-slate-300 px-2 text-center text-base tabular-nums text-slate-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none'

const digits = (value: string) => value.replace(/\D/g, '').slice(0, 4)

export default function StudentLogPage() {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [logs, setLogs] = useState<QuestionLog[] | null>(null)
  const [logDate, setLogDate] = useState(() => daysAgo(0))
  const [subjectId, setSubjectId] = useState<number | null>(null)
  const [topicId, setTopicId] = useState('')
  const [solved, setSolved] = useState('')
  const [correct, setCorrect] = useState('')
  const [wrong, setWrong] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const firstNumber = useRef<HTMLInputElement>(null)

  useEffect(() => {
    Promise.all([fetchMySubjects(), fetchMyQuestionLogs()])
      .then(([subjectData, logData]) => {
        setSubjects(subjectData)
        setLogs(logData)
      })
      .catch((err) => setError(errorMessage(err)))
  }, [])

  const today = daysAgo(0)
  const yesterday = daysAgo(1)
  const subject = subjects.find((s) => s.id === subjectId)

  // "Çözülen" may be left empty: it then counts as doğru + yanlış.
  const answered = Number(correct) + Number(wrong)
  const total = solved === '' ? answered : Number(solved)
  const tooMany = solved !== '' && answered > total
  const canSave = subjectId !== null && total > 0 && !tooMany && !saving

  const chooseSubject = (id: number) => {
    setSubjectId(id)
    setTopicId('')
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!canSave || subjectId === null) return
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const saved = await addQuestionLog({
        log_date: logDate,
        subject_id: subjectId,
        topic_id: topicId === '' ? null : Number(topicId),
        solved: total,
        correct: Number(correct),
        wrong: Number(wrong),
      })
      // Keep the list newest day first, newest entry first within a day.
      setLogs((prev) => [...(prev ?? []), saved].sort((a, b) => b.log_date.localeCompare(a.log_date) || b.id - a.id))
      setMessage('Kaydedildi.')
      // Date and subject stay, so several topics of one subject can be entered in a row.
      setTopicId('')
      setSolved('')
      setCorrect('')
      setWrong('')
      firstNumber.current?.focus()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (log: QuestionLog) => {
    if (!window.confirm('Bu kayıt silinsin mi?')) return
    setError(null)
    setMessage(null)
    try {
      await deleteQuestionLog(log.id)
      setLogs((prev) => (prev ?? []).filter((l) => l.id !== log.id))
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const chip = (active: boolean) =>
    `min-h-11 rounded-md border px-3 text-sm font-medium ${
      active ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-100'
    }`

  return (
    <DashboardLayout title="Soru takibi" narrow>
      <form onSubmit={handleSubmit} className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" aria-pressed={logDate === today} onClick={() => setLogDate(today)} className={chip(logDate === today)}>
            Bugün
          </button>
          <button
            type="button"
            aria-pressed={logDate === yesterday}
            onClick={() => setLogDate(yesterday)}
            className={chip(logDate === yesterday)}
          >
            Dün
          </button>
          <input
            type="date"
            aria-label="Tarih"
            required
            max={today}
            value={logDate}
            onChange={(e) => setLogDate(e.target.value)}
            className="h-11 min-w-0 flex-1 rounded-md border border-slate-300 px-2 text-base text-slate-900"
          />
        </div>

        <fieldset className="mt-4">
          <legend className="text-sm font-medium text-slate-700">Ders</legend>
          <div className="mt-1 grid grid-cols-3 gap-2">
            {subjects.map((s) => (
              <button
                key={s.id}
                type="button"
                aria-pressed={s.id === subjectId}
                onClick={() => chooseSubject(s.id)}
                className={chip(s.id === subjectId)}
              >
                {s.short_name}
              </button>
            ))}
          </div>
        </fieldset>

        <label className="mt-4 block text-sm font-medium text-slate-700">
          Konu
          <select
            value={topicId}
            disabled={!subject}
            onChange={(e) => setTopicId(e.target.value)}
            className="mt-1 h-12 w-full rounded-md border border-slate-300 bg-white px-2 text-base text-slate-900 disabled:bg-slate-50 disabled:text-slate-400"
          >
            <option value="">{subject ? 'Karışık (konu seçme)' : 'Önce ders seçin'}</option>
            {subject?.topics.map((topic) => (
              <option key={topic.id} value={topic.id}>
                {topic.name}
              </option>
            ))}
          </select>
        </label>

        <div className="mt-4 grid grid-cols-3 gap-2">
          <label className="block text-sm font-medium text-slate-700">
            Çözülen
            <input
              ref={firstNumber}
              inputMode="numeric"
              value={solved}
              placeholder={answered > 0 ? String(answered) : ''}
              onChange={(e) => setSolved(digits(e.target.value))}
              className={numberClass}
            />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Doğru
            <input inputMode="numeric" value={correct} onChange={(e) => setCorrect(digits(e.target.value))} className={numberClass} />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Yanlış
            <input inputMode="numeric" value={wrong} onChange={(e) => setWrong(digits(e.target.value))} className={numberClass} />
          </label>
        </div>
        <p className={`mt-2 text-sm ${tooMany ? 'text-red-700' : 'text-slate-500'}`} role={tooMany ? 'alert' : undefined}>
          {tooMany
            ? 'Doğru ve yanlış toplamı çözülen soru sayısını geçemez.'
            : total > 0
              ? `Boş: ${total - answered}`
              : 'Çözüleni boş bırakırsan doğru + yanlış olarak sayılır.'}
        </p>

        <button
          type="submit"
          disabled={!canSave}
          className="mt-4 h-12 w-full rounded-md bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {saving ? 'Kaydediliyor…' : 'Kaydet'}
        </button>

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
      </form>

      {logs && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <LogTotals label="Bugün" logs={logs.filter((log) => log.log_date === today)} />
            <LogTotals label="Son 7 gün" logs={logs.filter((log) => log.log_date >= daysAgo(6))} />
          </div>
          <h2 className="mt-6 mb-2 text-lg font-semibold text-slate-900">Son 30 gün</h2>
          <QuestionLogList logs={logs} subjects={subjects} emptyText="Henüz kayıt yok. İlk kaydını yukarıdan ekle." onDelete={handleDelete} />
        </>
      )}
    </DashboardLayout>
  )
}
