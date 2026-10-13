import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createExam, errorMessage, fetchExams, type Exam } from '../api'
import DashboardLayout from '../components/DashboardLayout'
import { formatDate } from '../format'

const inputClass =
  'mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none'

// Today's date as YYYY-MM-DD in local time.
const today = () => new Date().toLocaleDateString('sv-SE')

export default function ExamsPage() {
  const navigate = useNavigate()
  const [exams, setExams] = useState<Exam[] | null>(null)
  const [name, setName] = useState('')
  const [examDate, setExamDate] = useState(today)
  const [publisher, setPublisher] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetchExams()
      .then(setExams)
      .catch((err) => setError(errorMessage(err)))
  }, [])

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const exam = await createExam({ name, exam_date: examDate, publisher })
      // Go straight to result entry for the new exam.
      navigate(`/admin/exams/${exam.id}`)
    } catch (err) {
      setError(errorMessage(err))
      setSubmitting(false)
    }
  }

  return (
    <DashboardLayout title="Denemeler">
      <form
        onSubmit={handleSubmit}
        className="grid gap-4 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-[2fr_2fr_1fr_auto] sm:items-end"
      >
        <label className="block text-sm font-medium text-slate-700">
          Deneme adı
          <input required maxLength={255} value={name} onChange={(e) => setName(e.target.value)} className={inputClass} />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          Yayınevi
          <input maxLength={255} value={publisher} onChange={(e) => setPublisher(e.target.value)} className={inputClass} />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          Tarih
          <input
            type="date"
            required
            value={examDate}
            onChange={(e) => setExamDate(e.target.value)}
            className={inputClass}
          />
        </label>
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
        >
          Deneme oluştur
        </button>
      </form>

      {error && (
        <p role="alert" className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="mt-6 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
            <tr>
              <th className="px-4 py-2 font-medium">Deneme</th>
              <th className="px-4 py-2 font-medium">Yayınevi</th>
              <th className="px-4 py-2 font-medium">Tarih</th>
              <th className="px-4 py-2 text-right font-medium">Sonucu girilen öğrenci</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {exams?.map((exam) => (
              <tr key={exam.id} className="hover:bg-slate-50">
                <td className="px-4 py-2">
                  <Link to={`/admin/exams/${exam.id}`} className="font-medium text-indigo-700 hover:underline">
                    {exam.name}
                  </Link>
                </td>
                <td className="px-4 py-2 text-slate-600">{exam.publisher ?? '—'}</td>
                <td className="px-4 py-2 text-slate-600">{formatDate(exam.exam_date)}</td>
                <td className="px-4 py-2 text-right tabular-nums text-slate-600">{exam.student_count}</td>
              </tr>
            ))}
            {exams?.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                  Henüz deneme yok.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </DashboardLayout>
  )
}
