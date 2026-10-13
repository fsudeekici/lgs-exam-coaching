import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  deleteStudentResults,
  errorMessage,
  fetchExam,
  fetchStudents,
  fetchSubjects,
  saveStudentResults,
  type ExamDetail,
  type ResultInput,
  type Student,
  type StudentResults,
  type Subject,
} from '../api'
import DashboardLayout from '../components/DashboardLayout'
import ResultEntryForm from '../components/ResultEntryForm'
import ResultsTable from '../components/ResultsTable'
import { formatDate } from '../format'

export default function ExamDetailPage() {
  const examId = Number(useParams().examId)
  const [exam, setExam] = useState<ExamDetail | null>(null)
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [students, setStudents] = useState<Student[]>([])
  const [studentId, setStudentId] = useState<number | null>(null)
  // Bumped after each save or delete so the form reloads even when the same student stays selected.
  const [formVersion, setFormVersion] = useState(0)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchExam(examId), fetchSubjects(), fetchStudents()])
      .then(([examData, subjectData, studentData]) => {
        setExam(examData)
        setSubjects(subjectData)
        setStudents(studentData)
        setStudentId(nextStudentWithoutResults(studentData, examData.students) ?? studentData[0]?.id ?? null)
      })
      .catch((err) => setError(errorMessage(err)))
  }, [examId])

  if (!exam) {
    return (
      <DashboardLayout title="Deneme">
        {error ? <p className="text-red-700">{error}</p> : <p className="text-slate-500">Yükleniyor…</p>}
      </DashboardLayout>
    )
  }

  const entered = new Map(exam.students.map((s) => [s.student_id, s]))

  const handleSave = async (results: ResultInput[]) => {
    if (studentId === null) return
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const saved = await saveStudentResults(examId, studentId, results)
      const updated = [...exam.students.filter((s) => s.student_id !== saved.student_id), saved].sort((a, b) =>
        a.full_name.localeCompare(b.full_name, 'tr'),
      )
      setExam({ ...exam, students: updated })
      setMessage(`${saved.full_name} kaydedildi.`)
      // Move on to the next student that still needs results.
      setStudentId(nextStudentWithoutResults(students, updated, studentId) ?? studentId)
      setFormVersion((v) => v + 1)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (student: StudentResults) => {
    if (!window.confirm(`${student.full_name} için girilen sonuçlar silinsin mi?`)) return
    setError(null)
    setMessage(null)
    try {
      await deleteStudentResults(examId, student.student_id)
      setExam({ ...exam, students: exam.students.filter((s) => s.student_id !== student.student_id) })
      setFormVersion((v) => v + 1)
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const selectStudent = (id: number) => {
    setStudentId(id)
    setMessage(null)
    setError(null)
  }

  return (
    <DashboardLayout title={exam.name}>
      <p className="-mt-4 text-sm text-slate-500">
        <Link to="/admin" className="text-indigo-700 hover:underline">
          ← Denemeler
        </Link>
        <span className="mx-2">·</span>
        {formatDate(exam.exam_date)}
        {exam.publisher && ` · ${exam.publisher}`}
      </p>

      <section className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-900">Sonuç girişi</h2>
        {students.length === 0 ? (
          <p className="mt-2 text-slate-500">Kayıtlı öğrenci yok.</p>
        ) : (
          <>
            <label className="mt-3 block text-sm font-medium text-slate-700">
              Öğrenci
              <select
                value={studentId ?? ''}
                onChange={(e) => selectStudent(Number(e.target.value))}
                className="mt-1 block w-full max-w-sm rounded-md border border-slate-300 px-3 py-2 text-slate-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
              >
                {students.map((student) => (
                  <option key={student.id} value={student.id}>
                    {student.full_name}
                    {entered.has(student.id) ? ' ✓' : ''}
                  </option>
                ))}
              </select>
            </label>

            {studentId !== null && (
              <div className="mt-4">
                <ResultEntryForm
                  key={`${studentId}-${formVersion}`}
                  subjects={subjects}
                  initial={entered.get(studentId)?.results}
                  saving={saving}
                  onSave={handleSave}
                />
              </div>
            )}
          </>
        )}
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
      </section>

      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold text-slate-900">Sonuçlar ({exam.students.length})</h2>
        <ResultsTable subjects={subjects} students={exam.students} onEdit={selectStudent} onDelete={handleDelete} />
      </section>
    </DashboardLayout>
  )
}

/** First student after `afterId` (wrapping around) that has no results yet. */
function nextStudentWithoutResults(students: Student[], entered: StudentResults[], afterId?: number) {
  const done = new Set(entered.map((s) => s.student_id))
  const start = students.findIndex((s) => s.id === afterId) + 1
  const ordered = [...students.slice(start), ...students.slice(0, start)]
  return ordered.find((s) => !done.has(s.id))?.id
}
