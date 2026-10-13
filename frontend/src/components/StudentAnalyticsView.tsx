import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { ExamPoint, NetChange, StudentAnalytics } from '../api'
import { formatDate, formatNet } from '../format'
import { AverageComparisonChart, NetTrendChart } from './charts'
import Delta from './Delta'

const TOTAL_QUESTIONS = 90

interface Props {
  data: StudentAnalytics
  /** Link exam names to the admin exam page. Off for the student's own read-only view. */
  examLinks: boolean
}

/** Exam analytics for one student: last exam, net trend, weak topics and averages. */
export default function StudentAnalyticsView({ data, examLinks }: Props) {
  const { subjects, exams, comparison, weak_topics: weakTopics, averages } = data
  const subjectById = new Map(subjects.map((s) => [s.id, s]))
  const examById = new Map(exams.map((e) => [e.exam_id, e]))
  const netOf = (exam: ExamPoint, subjectId: number) => exam.nets.find((n) => n.subject_id === subjectId)?.net
  const lastExam = comparison && examById.get(comparison.last_exam_id)
  const previousExam = comparison?.previous_exam_id != null ? examById.get(comparison.previous_exam_id) : undefined

  if (exams.length === 0 || !comparison || !lastExam) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
        Henüz deneme sonucu girilmedi.
      </div>
    )
  }

  return (
    <>
      <Section
        title="Son deneme"
        note={
          previousExam
            ? `${lastExam.name} (${formatDate(lastExam.exam_date)}) · önceki: ${previousExam.name} (${formatDate(previousExam.exam_date)})`
            : `${lastExam.name} (${formatDate(lastExam.exam_date)}) · karşılaştırılacak önceki deneme yok`
        }
      >
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
          <ChangeTile label="Toplam" change={comparison.total} max={TOTAL_QUESTIONS} emphasized />
          {comparison.subjects.map((change) => {
            const subject = subjectById.get(change.subject_id)
            return (
              <ChangeTile
                key={change.subject_id}
                label={subject?.short_name ?? ''}
                change={change}
                max={subject?.question_count ?? 0}
              />
            )
          })}
        </div>
      </Section>

      <Section title="Net gelişimi" note="Denemeler tarih sırasıyla; her nokta bir deneme.">
        <Card>
          <h3 className="text-sm font-medium text-slate-700">Toplam net</h3>
          <NetTrendChart
            exams={exams}
            value={(exam) => exam.total_net}
            label="Toplam net"
            domain={[0, TOTAL_QUESTIONS]}
            ticks={[0, 15, 30, 45, 60, 75, 90]}
            height={260}
            labelLast
          />
        </Card>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {subjects.map((subject) => (
            <Card key={subject.id}>
              <h3 className="text-sm font-medium text-slate-700">
                {subject.short_name} <span className="font-normal text-slate-400">({subject.question_count} soru)</span>
              </h3>
              <NetTrendChart
                exams={exams}
                value={(exam) => netOf(exam, subject.id)}
                label={subject.short_name}
                domain={[0, subject.question_count]}
                ticks={subject.question_count === 20 ? [0, 5, 10, 15, 20] : [0, 5, 10]}
                height={150}
                labelLast
              />
            </Card>
          ))}
        </div>

        <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm whitespace-nowrap">
            <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-2 text-left font-medium">Deneme</th>
                <th className="px-4 py-2 text-left font-medium">Tarih</th>
                {subjects.map((subject) => (
                  <th key={subject.id} className="px-3 py-2 text-right font-medium">
                    {subject.short_name}
                  </th>
                ))}
                <th className="px-4 py-2 text-right font-medium">Toplam</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {[...exams].reverse().map((exam) => (
                <tr key={exam.exam_id} className="hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">
                    {examLinks ? (
                      <Link to={`/admin/exams/${exam.exam_id}`} className="text-indigo-700 hover:underline">
                        {exam.name}
                      </Link>
                    ) : (
                      exam.name
                    )}
                  </td>
                  <td className="px-4 py-2 text-slate-600">{formatDate(exam.exam_date)}</td>
                  {subjects.map((subject) => {
                    const net = netOf(exam, subject.id)
                    return (
                      <td key={subject.id} className="px-3 py-2 text-right tabular-nums">
                        {net === undefined ? '—' : formatNet(net)}
                      </td>
                    )
                  })}
                  <td className="px-4 py-2 text-right font-semibold tabular-nums text-slate-900">
                    {formatNet(exam.total_net)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <div className="grid gap-x-6 lg:grid-cols-2">
        <Section title="Zayıf konular" note="Son 3 denemenin en az 2’sinde yanlış yapılan konular.">
          <Card>
            <WeakTopicList topics={weakTopics} subjectName={(id) => subjectById.get(id)?.short_name} />
          </Card>
        </Section>

        <Section
          title="Öğrenci ve genel ortalama"
          note="Ders bazında ortalama net. Genel ortalama, bu öğrencinin girdiği denemelere giren tüm öğrencilerden hesaplanır."
        >
          <Card>
            <AverageComparisonChart
              height={260}
              rows={averages.map((a) => ({
                subject: subjectById.get(a.subject_id)?.short_name ?? '',
                student: a.student_average,
                average: a.class_average,
              }))}
            />
            <table className="mt-3 w-full text-sm">
              <thead className="border-b border-slate-200 text-slate-600">
                <tr>
                  <th className="py-1.5 text-left font-medium">Ders</th>
                  <th className="py-1.5 text-right font-medium">Öğrenci</th>
                  <th className="py-1.5 text-right font-medium">Tüm öğrenciler</th>
                  <th className="py-1.5 text-right font-medium">Fark</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {averages.map((a) => (
                  <tr key={a.subject_id}>
                    <td className="py-1.5 text-slate-900">{subjectById.get(a.subject_id)?.short_name}</td>
                    <td className="py-1.5 text-right tabular-nums">{formatNet(a.student_average)}</td>
                    <td className="py-1.5 text-right tabular-nums">{formatNet(a.class_average)}</td>
                    <td className="py-1.5 text-right">
                      <Delta change={Math.round((a.student_average - a.class_average) * 100) / 100} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </Section>
      </div>
    </>
  )
}

export function Section({ title, note, children }: { title: string; note?: string; children: ReactNode }) {
  return (
    <section className="mt-8">
      {/* On paper, a heading stays with the content below it. */}
      <h2 className="break-after-avoid text-lg font-semibold text-slate-900">{title}</h2>
      {note && <p className="mt-0.5 break-after-avoid text-sm text-slate-500">{note}</p>}
      <div className="mt-3">{children}</div>
    </section>
  )
}

interface WeakTopicListProps {
  /** Most frequent first. */
  topics: StudentAnalytics['weak_topics']
  subjectName: (subjectId: number) => string | undefined
}

/** The student's weak topics, with a bar for how many of the last exams missed each. */
export function WeakTopicList({ topics, subjectName }: WeakTopicListProps) {
  if (topics.length === 0) {
    return <p className="py-6 text-center text-sm text-slate-500">Son 3 denemede tekrar eden yanlış konu yok.</p>
  }
  return (
    <ol className="space-y-3">
      {topics.map((topic) => (
        <li key={topic.topic_id}>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="text-slate-900">
              {topic.name} <span className="text-slate-400">· {subjectName(topic.subject_id)}</span>
            </span>
            <span className="shrink-0 font-semibold tabular-nums text-slate-900">
              {topic.count} <span className="font-normal text-slate-500">denemede</span>
            </span>
          </div>
          <div className="mt-1 h-2 rounded-r bg-[#2a78d6]" style={{ width: `${(topic.count / topics[0].count) * 100}%` }} />
        </li>
      ))}
    </ol>
  )
}

export function Card({ children }: { children: ReactNode }) {
  return <div className="break-inside-avoid rounded-lg border border-slate-200 bg-white p-4">{children}</div>
}

function ChangeTile({ label, change, max, emphasized }: { label: string; change: NetChange; max: number; emphasized?: boolean }) {
  return (
    <div className={`rounded-lg border bg-white p-3 ${emphasized ? 'border-slate-400' : 'border-slate-200'}`}>
      <div className="text-sm text-slate-600">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">
        {formatNet(change.last)}
        <span className="ml-1 text-sm font-normal text-slate-400">/ {max}</span>
      </div>
      <div className="mt-1 text-sm">
        <Delta change={change.change} />
      </div>
    </div>
  )
}
