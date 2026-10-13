import { useEffect, useState, type ReactNode } from 'react'
import { errorMessage, fetchMyChildren, type ChildSummary } from '../api'
import { NetTrendChart, WeekQuestionsChart } from '../components/charts'
import DashboardLayout from '../components/DashboardLayout'
import { Delta } from '../components/StudentAnalyticsView'
import { formatDate, formatNet, formatTimestamp } from '../format'

const WEAK_TOPIC_COUNT = 5
const NOTE_COUNT = 3

/** A short summary of each child linked to the logged-in parent. */
export default function ParentHomePage() {
  const [children, setChildren] = useState<ChildSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchMyChildren()
      .then(setChildren)
      .catch((err) => setError(errorMessage(err)))
  }, [])

  return (
    <DashboardLayout title="Veli paneli" narrow>
      {error && <p className="text-red-700">{error}</p>}
      {!children && !error && <p className="text-slate-500">Yükleniyor…</p>}
      {children?.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
          Hesabınıza bağlı öğrenci bulunmuyor. Lütfen koçunuzla iletişime geçin.
        </div>
      )}
      <div className="space-y-10">
        {children?.map((child) => (
          <ChildSection key={child.analytics.student.id} child={child} />
        ))}
      </div>
    </DashboardLayout>
  )
}

function ChildSection({ child }: { child: ChildSummary }) {
  const { analytics, week, notes } = child
  const { student, subjects, exams, comparison, weak_topics: weakTopics } = analytics
  const subjectById = new Map(subjects.map((s) => [s.id, s]))
  const lastExam = exams.at(-1)

  return (
    <section aria-label={student.full_name}>
      <h2 className="text-xl font-semibold text-slate-900">{student.full_name}</h2>
      <p className="text-sm text-slate-500">{[student.school, student.class_name].filter(Boolean).join(' · ')}</p>

      {notes.length > 0 && (
        <Block title="Koçun notu">
          <ul className="space-y-3">
            {notes.slice(0, NOTE_COUNT).map((note) => (
              <li key={note.id}>
                <div className="text-xs text-slate-500">{formatTimestamp(note.created_at)}</div>
                <p className="whitespace-pre-line text-slate-900">{note.body}</p>
              </li>
            ))}
          </ul>
        </Block>
      )}

      <Block title="Son deneme" note={lastExam && `${lastExam.name} · ${formatDate(lastExam.exam_date)}`}>
        {!comparison ? (
          <p className="text-sm text-slate-500">Henüz deneme sonucu yok.</p>
        ) : (
          <>
            <div className="flex items-baseline gap-3">
              <span className="text-4xl font-semibold text-slate-900">{formatNet(comparison.total.last)}</span>
              <span className="text-slate-500">net / 90</span>
            </div>
            <div className="mt-1 text-sm">
              {comparison.total.change === null ? (
                <span className="text-slate-500">İlk deneme</span>
              ) : (
                <>
                  <Delta change={comparison.total.change} /> <span className="text-slate-500">önceki denemeye göre</span>
                </>
              )}
            </div>
            <dl className="mt-4 grid grid-cols-3 gap-x-3 gap-y-4 border-t border-slate-100 pt-4">
              {comparison.subjects.map((change) => (
                <div key={change.subject_id}>
                  <dt className="text-sm text-slate-600">{subjectById.get(change.subject_id)?.short_name}</dt>
                  <dd className="text-lg font-semibold text-slate-900">{formatNet(change.last)}</dd>
                  <dd className="text-xs">
                    <Delta change={change.change} />
                  </dd>
                </div>
              ))}
            </dl>
          </>
        )}
      </Block>

      {exams.length > 1 && (
        <Block title="Net gelişimi" note="Denemelerdeki toplam net.">
          <NetTrendChart
            exams={exams}
            value={(exam) => exam.total_net}
            label="Toplam net"
            domain={[0, 90]}
            ticks={[0, 30, 60, 90]}
            height={200}
            labelLast
          />
        </Block>
      )}

      <Block title="Zayıf konular" note="Denemelerde en sık yanlış yapılan konular.">
        {weakTopics.length === 0 ? (
          <p className="text-sm text-slate-500">Henüz işaretlenmiş bir konu yok.</p>
        ) : (
          <ol className="divide-y divide-slate-100">
            {weakTopics.slice(0, WEAK_TOPIC_COUNT).map((topic) => (
              <li key={topic.topic_id} className="flex items-baseline justify-between gap-3 py-2 text-sm">
                <span className="text-slate-900">
                  {topic.name} <span className="text-slate-400">· {subjectById.get(topic.subject_id)?.short_name}</span>
                </span>
                <span className="shrink-0 text-slate-600 tabular-nums">{topic.count} kez</span>
              </li>
            ))}
          </ol>
        )}
      </Block>

      <Block title="Son 7 gün" note="Çözülen soru sayısı.">
        <div className="flex items-baseline gap-3">
          <span className="text-4xl font-semibold text-slate-900">{week.solved}</span>
          <span className="text-slate-500">soru</span>
        </div>
        <p className="mt-1 text-sm text-slate-600">
          {week.correct} doğru · {week.wrong} yanlış · 7 günün {week.active_days} günü çalıştı
        </p>
        {week.solved > 0 && (
          <div className="mt-3">
            <WeekQuestionsChart days={week.days} height={150} />
          </div>
        )}
      </Block>
    </section>
  )
}

function Block({ title, note, children }: { title: string; note?: string; children: ReactNode }) {
  return (
    <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="font-semibold text-slate-900">{title}</h3>
      {note && <p className="text-sm text-slate-500">{note}</p>}
      <div className="mt-3">{children}</div>
    </div>
  )
}
