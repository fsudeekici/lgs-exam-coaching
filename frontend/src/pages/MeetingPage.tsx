import { useEffect, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { errorMessage, fetchMeetingPage, type MeetingPageData, type TopicStatus } from '../api'
import { AverageComparisonChart, DailyQuestionsChart, NetTrendChart } from '../components/charts'
import Delta from '../components/Delta'
import MeetingNotes from '../components/MeetingNotes'
import { Card, Section, WeakTopicList } from '../components/StudentAnalyticsView'
import { daysAgo, formatDate, formatNet, formatTimestamp } from '../format'
import { STATUS_BY_VALUE } from '../study'

const TOTAL_QUESTIONS = 90
// Left to right in the progress bars.
const BAR_ORDER: TopicStatus[] = ['done', 'studying', 'needs_review', 'not_started']

/** One page about a student to show on screen, or print, at a parent meeting. */
export default function MeetingPage() {
  const studentId = Number(useParams().studentId)
  const [data, setData] = useState<MeetingPageData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchMeetingPage(studentId)
      .then(setData)
      .catch((err) => setError(errorMessage(err)))
  }, [studentId])

  return (
    <div className="min-h-screen bg-slate-50 print:bg-white">
      <div className="border-b border-slate-200 bg-white print:hidden">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3 text-sm">
          <Link to={`/admin/students/${studentId}`} className="text-indigo-700 hover:underline">
            ← Öğrenci sayfası
          </Link>
          <button
            onClick={() => window.print()}
            disabled={!data}
            className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Yazdır / PDF kaydet
          </button>
        </div>
      </div>
      <main className="mx-auto max-w-5xl px-4 py-8 print:max-w-none print:p-0">
        {error && <p className="text-red-700">{error}</p>}
        {!data && !error && <p className="text-slate-500">Yükleniyor…</p>}
        {data && <Meeting data={data} />}
      </main>
    </div>
  )
}

function Meeting({ data }: { data: MeetingPageData }) {
  const { analytics, questions, questions_by_subject: bySubject, topic_progress: progress, notes } = data
  const { student, subjects, exams, comparison, weak_topics: weakTopics, averages } = analytics
  const subjectById = new Map(subjects.map((s) => [s.id, s]))
  const lastExam = exams.at(-1)
  const averageNet = exams.reduce((sum, exam) => sum + exam.total_net, 0) / (exams.length || 1)
  const averageById = new Map(averages.map((a) => [a.subject_id, a]))
  const topics = progress.reduce(
    (sum, p) => ({ total: sum.total + p.total, done: sum.done + p.done, needs_review: sum.needs_review + p.needs_review }),
    { total: 0, done: 0, needs_review: 0 },
  )
  const days = questions.days.length

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-1 border-b border-slate-300 pb-4">
        <div>
          <p className="text-sm font-medium tracking-wide text-slate-500 uppercase">Veli görüşmesi</p>
          <h1 className="text-3xl font-semibold text-slate-900">{student.full_name}</h1>
          <p className="text-slate-600">{[student.school, student.class_name].filter(Boolean).join(' · ')}</p>
        </div>
        <p className="text-sm text-slate-600">{formatDate(daysAgo(0))}</p>
      </header>

      <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4 print:grid-cols-4">
        <Tile label="Son deneme" value={comparison ? formatNet(comparison.total.last) : '—'} unit={comparison ? `/ ${TOTAL_QUESTIONS} net` : undefined}>
          {!comparison ? (
            'Henüz deneme sonucu yok'
          ) : comparison.total.change === null ? (
            'İlk deneme'
          ) : (
            <>
              <Delta change={comparison.total.change} /> önceki denemeye göre
            </>
          )}
        </Tile>
        <Tile label="Deneme ortalaması" value={exams.length ? formatNet(averageNet) : '—'} unit={exams.length ? 'net' : undefined}>
          {exams.length} deneme
        </Tile>
        <Tile label={`Son ${days} gün`} value={String(questions.solved)} unit="soru">
          {days} günün {questions.active_days} günü çalıştı
        </Tile>
        <Tile label="Biten konu" value={String(topics.done)} unit={`/ ${topics.total}`}>
          {topics.needs_review} konu tekrar gerekli
        </Tile>
      </div>

      {exams.length === 0 || !comparison || !lastExam ? (
        <Section title="Denemeler">
          <Empty>Henüz deneme sonucu girilmedi.</Empty>
        </Section>
      ) : (
        <>
          <Section title="Net gelişimi" note="Denemeler tarih sırasıyla; her nokta bir deneme.">
            <Card>
              <h3 className="text-sm font-medium text-slate-700">Toplam net</h3>
              <NetTrendChart
                exams={exams}
                value={(exam) => exam.total_net}
                label="Toplam net"
                domain={[0, TOTAL_QUESTIONS]}
                ticks={[0, 15, 30, 45, 60, 75, 90]}
                height={240}
                labelLast
              />
            </Card>
            <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-3 print:grid-cols-3">
              {subjects.map((subject) => (
                <Card key={subject.id}>
                  <h3 className="text-sm font-medium text-slate-700">
                    {subject.short_name} <span className="font-normal text-slate-400">({subject.question_count} soru)</span>
                  </h3>
                  <NetTrendChart
                    exams={exams}
                    value={(exam) => exam.nets.find((n) => n.subject_id === subject.id)?.net}
                    label={subject.short_name}
                    domain={[0, subject.question_count]}
                    ticks={subject.question_count === 20 ? [0, 5, 10, 15, 20] : [0, 5, 10]}
                    height={130}
                    labelLast
                  />
                </Card>
              ))}
            </div>
          </Section>

          <Section
            title="Ders karşılaştırması"
            note={`Son deneme: ${lastExam.name} (${formatDate(lastExam.exam_date)}). Ortalamalar öğrencinin girdiği tüm denemelerden; genel ortalama aynı denemelere giren tüm öğrencilerden hesaplanır.`}
          >
            <Card>
              <div className="grid items-center gap-6 lg:grid-cols-2 print:grid-cols-2">
                <AverageComparisonChart
                  height={240}
                  rows={averages.map((a) => ({
                    subject: subjectById.get(a.subject_id)?.short_name ?? '',
                    student: a.student_average,
                    average: a.class_average,
                  }))}
                />
                <table className="w-full text-sm">
                  <thead className="border-b border-slate-200 text-slate-600">
                    <tr>
                      <th className="py-1.5 text-left font-medium">Ders</th>
                      <th className="py-1.5 text-right font-medium">Son deneme</th>
                      <th className="py-1.5 text-right font-medium">Değişim</th>
                      <th className="py-1.5 text-right font-medium">Öğrenci ort.</th>
                      <th className="py-1.5 text-right font-medium">Genel ort.</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {comparison.subjects.map((change) => {
                      const average = averageById.get(change.subject_id)
                      return (
                        <tr key={change.subject_id}>
                          <td className="py-1.5 text-slate-900">{subjectById.get(change.subject_id)?.short_name}</td>
                          <td className="py-1.5 text-right font-semibold tabular-nums text-slate-900">{formatNet(change.last)}</td>
                          <td className="py-1.5 text-right">
                            <Delta change={change.change} />
                          </td>
                          <td className="py-1.5 text-right tabular-nums">{average ? formatNet(average.student_average) : '—'}</td>
                          <td className="py-1.5 text-right tabular-nums">{average ? formatNet(average.class_average) : '—'}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          </Section>

          <Section title="Zayıf konular" note="Son 3 denemenin en az 2’sinde yanlış yapılan konular.">
            <Card>
              <WeakTopicList topics={weakTopics} subjectName={(id) => subjectById.get(id)?.short_name} />
            </Card>
          </Section>
        </>
      )}

      <Section title={`Son ${days} gün soru çözümü`} note="Öğrencinin girdiği günlük soru kayıtları.">
        {questions.solved === 0 ? (
          <Empty>Öğrenci son {days} günde soru kaydı girmedi.</Empty>
        ) : (
          <Card>
            <div className="grid items-center gap-6 lg:grid-cols-[3fr_2fr] print:grid-cols-[3fr_2fr]">
              <DailyQuestionsChart days={questions.days} height={220} axis="date" />
              <table className="w-full text-sm">
                <thead className="border-b border-slate-200 text-slate-600">
                  <tr>
                    <th className="py-1.5 text-left font-medium">Ders</th>
                    <th className="py-1.5 text-right font-medium">Soru</th>
                    <th className="py-1.5 text-right font-medium">Doğru</th>
                    <th className="py-1.5 text-right font-medium">Yanlış</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {bySubject.map((row) => (
                    <tr key={row.subject_id}>
                      <td className="py-1.5 text-slate-900">{subjectById.get(row.subject_id)?.short_name}</td>
                      <td className="py-1.5 text-right tabular-nums">{row.solved}</td>
                      <td className="py-1.5 text-right tabular-nums">{row.correct}</td>
                      <td className="py-1.5 text-right tabular-nums">{row.wrong}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="border-t border-slate-300 font-semibold text-slate-900">
                  <tr>
                    <td className="py-1.5">Toplam</td>
                    <td className="py-1.5 text-right tabular-nums">{questions.solved}</td>
                    <td className="py-1.5 text-right tabular-nums">{questions.correct}</td>
                    <td className="py-1.5 text-right tabular-nums">{questions.wrong}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </Card>
        )}
      </Section>

      <Section title="Konu ilerlemesi" note="Öğrencinin konular için işaretlediği durum.">
        <Card>
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 text-slate-600">
              <tr>
                <th className="py-1.5 text-left font-medium">Ders</th>
                <th className="w-1/2 py-1.5" />
                {BAR_ORDER.map((status) => (
                  <th key={status} className="py-1.5 pl-3 text-right font-medium">
                    <span className={`mr-1.5 inline-block h-2.5 w-2.5 rounded-sm ${STATUS_BY_VALUE.get(status)!.bar}`} />
                    {STATUS_BY_VALUE.get(status)!.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {progress.map((row) => (
                <tr key={row.subject_id}>
                  <td className="py-2 pr-3 text-slate-900">{subjectById.get(row.subject_id)?.short_name}</td>
                  <td className="py-2">
                    <div className="flex h-3 gap-0.5">
                      {BAR_ORDER.filter((status) => row[status] > 0).map((status) => (
                        <div
                          key={status}
                          className={`rounded-sm ${STATUS_BY_VALUE.get(status)!.bar}`}
                          style={{ flexGrow: row[status], flexBasis: 0 }}
                        />
                      ))}
                    </div>
                  </td>
                  {BAR_ORDER.map((status) => (
                    <td key={status} className="py-2 pl-3 text-right tabular-nums">
                      {row[status]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </Section>

      {notes.length > 0 && (
        <Section title="Koç notları" note="Veliyle paylaşılan notlar.">
          <Card>
            <ul className="divide-y divide-slate-100">
              {notes.map((note) => (
                <li key={note.id} className="break-inside-avoid py-3 first:pt-0 last:pb-0">
                  <div className="text-sm text-slate-500">{formatTimestamp(note.created_at)}</div>
                  <p className="mt-1 whitespace-pre-line text-slate-900">{note.body}</p>
                </li>
              ))}
            </ul>
          </Card>
        </Section>
      )}

      <Section title="Görüşme notları" note="Her veli görüşmesinden sonra eklenen notlar.">
        <MeetingNotes studentId={student.id} initialNotes={data.meeting_notes} />
      </Section>
    </>
  )
}

function Tile({ label, value, unit, children }: { label: string; value: string; unit?: string; children: ReactNode }) {
  return (
    <div className="break-inside-avoid rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-sm text-slate-600">{label}</div>
      <div className="mt-1 text-3xl font-semibold text-slate-900">
        {value}
        {unit && <span className="ml-1.5 text-sm font-normal text-slate-500">{unit}</span>}
      </div>
      <div className="mt-1 text-sm text-slate-600">{children}</div>
    </div>
  )
}

function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">{children}</div>
  )
}
