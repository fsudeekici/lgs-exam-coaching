import type { StudentResults, Subject } from '../api'
import { formatNet } from '../format'

interface Props {
  subjects: Subject[]
  students: StudentResults[]
  onEdit: (studentId: number) => void
  onDelete: (student: StudentResults) => void
}

export default function ResultsTable({ subjects, students, onEdit, onDelete }: Props) {
  const topicNames = new Map(subjects.flatMap((s) => s.topics.map((t) => [t.id, t.name] as const)))

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full text-sm whitespace-nowrap">
        <thead className="bg-slate-50 text-slate-600">
          <tr>
            <th rowSpan={2} className="px-3 py-2 text-left font-medium">
              Öğrenci
            </th>
            {subjects.map((subject) => (
              <th key={subject.id} colSpan={4} className="border-l border-slate-200 px-2 py-2 text-center font-medium">
                {subject.name}
              </th>
            ))}
            <th rowSpan={2} className="border-l border-slate-200 px-3 py-2 text-right font-medium">
              Toplam net
            </th>
            <th rowSpan={2} className="px-3 py-2 text-left font-medium">
              Yanlış konular
            </th>
            <th rowSpan={2} />
          </tr>
          <tr className="border-b border-slate-200 text-xs">
            {subjects.map((subject) =>
              ['D', 'Y', 'B', 'Net'].map((label) => (
                <th
                  key={`${subject.id}-${label}`}
                  className={`px-1.5 py-1 text-right font-medium ${label === 'D' ? 'border-l border-slate-200' : ''}`}
                >
                  {label}
                </th>
              )),
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {students.map((student) => {
            const bySubject = new Map(student.results.map((r) => [r.subject_id, r]))
            const mistakes = student.results.flatMap((r) => r.mistake_topic_ids.map((id) => topicNames.get(id) ?? ''))
            return (
              <tr key={student.student_id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-medium text-slate-900">{student.full_name}</td>
                {subjects.map((subject) => {
                  const result = bySubject.get(subject.id)
                  return [
                    <td key={`${subject.id}-c`} className="border-l border-slate-100 px-1.5 py-2 text-right tabular-nums">
                      {result?.correct ?? '—'}
                    </td>,
                    <td key={`${subject.id}-w`} className="px-1.5 py-2 text-right tabular-nums">
                      {result?.wrong ?? '—'}
                    </td>,
                    <td key={`${subject.id}-b`} className="px-1.5 py-2 text-right tabular-nums">
                      {result?.blank ?? '—'}
                    </td>,
                    <td key={`${subject.id}-n`} className="px-1.5 py-2 text-right font-medium tabular-nums text-slate-900">
                      {result ? formatNet(result.net) : '—'}
                    </td>,
                  ]
                })}
                <td className="border-l border-slate-100 px-3 py-2 text-right font-semibold tabular-nums text-slate-900">
                  {formatNet(student.total_net)}
                </td>
                <td className="min-w-40 px-3 py-2 text-xs whitespace-normal text-slate-600">
                  {mistakes.join(', ') || '—'}
                </td>
                <td className="px-3 py-2 text-right">
                  <button onClick={() => onEdit(student.student_id)} className="text-indigo-700 hover:underline">
                    Düzenle
                  </button>
                  <button onClick={() => onDelete(student)} className="ml-3 text-red-600 hover:underline">
                    Sil
                  </button>
                </td>
              </tr>
            )
          })}
          {students.length === 0 && (
            <tr>
              <td colSpan={subjects.length * 4 + 4} className="px-3 py-8 text-center text-slate-500">
                Bu deneme için henüz sonuç girilmedi.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
