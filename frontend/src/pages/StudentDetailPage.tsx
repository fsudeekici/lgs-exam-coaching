import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  errorMessage,
  fetchStudentAnalytics,
  fetchStudentQuestionLogs,
  fetchStudentTopicProgress,
  fetchSubjects,
  type QuestionLog,
  type StudentAnalytics,
  type Subject,
  type TopicProgress,
} from '../api'
import CoachNotes from '../components/CoachNotes'
import DashboardLayout from '../components/DashboardLayout'
import StudentAnalyticsView, { Card, Section } from '../components/StudentAnalyticsView'
import { LogTotals, QuestionLogList, StatusCounts, TopicStatusBadge } from '../components/study'
import { daysAgo } from '../format'
import { countByStatus, progressMap } from '../study'

interface PageData {
  analytics: StudentAnalytics
  subjects: Subject[]
  logs: QuestionLog[]
  progress: TopicProgress[]
}

/** Admin's view of one student: exam analytics plus what the student records in their panel. */
export default function StudentDetailPage() {
  const studentId = Number(useParams().studentId)
  const [data, setData] = useState<PageData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      fetchStudentAnalytics(studentId),
      fetchSubjects(),
      fetchStudentQuestionLogs(studentId),
      fetchStudentTopicProgress(studentId),
    ])
      .then(([analytics, subjects, logs, progress]) => setData({ analytics, subjects, logs, progress }))
      .catch((err) => setError(errorMessage(err)))
  }, [studentId])

  if (!data) {
    return (
      <DashboardLayout title="Öğrenci">
        {error ? <p className="text-red-700">{error}</p> : <p className="text-slate-500">Yükleniyor…</p>}
      </DashboardLayout>
    )
  }

  const { analytics, subjects, logs, progress } = data
  const { student } = analytics
  const statuses = progressMap(progress)

  return (
    <DashboardLayout title={student.full_name}>
      <div className="-mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-500">
          <Link to="/admin/students" className="text-indigo-700 hover:underline">
            ← Öğrenciler
          </Link>
          {[student.school, student.class_name, student.is_active ? null : 'Pasif'].filter(Boolean).map((part) => (
            <span key={part}>
              <span className="mx-2">·</span>
              {part}
            </span>
          ))}
        </p>
        <Link
          to={`/admin/students/${student.id}/meeting`}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Veli görüşmesi sayfası
        </Link>
      </div>

      <StudentAnalyticsView data={analytics} examLinks />

      <Section title="Koç notları" note="Öğrenci hakkındaki notlarınız. Veli yalnızca görünür işaretlediklerinizi görür.">
        <CoachNotes studentId={student.id} />
      </Section>

      <div className="grid gap-x-6 lg:grid-cols-2">
        <Section title="Soru takibi" note="Öğrencinin son 30 günde girdiği günlük soru kayıtları.">
          <div className="mb-3 grid grid-cols-2 gap-3">
            <LogTotals label="Son 7 gün" logs={logs.filter((log) => log.log_date >= daysAgo(6))} />
            <LogTotals label="Son 30 gün" logs={logs} />
          </div>
          <QuestionLogList logs={logs} subjects={subjects} emptyText="Öğrenci son 30 günde kayıt girmedi." />
        </Section>

        <Section title="Konu takibi" note="Öğrencinin konular için işaretlediği durum.">
          <StatusCounts counts={countByStatus(subjects, statuses)} />
          <div className="mt-3 space-y-2">
            {subjects.map((subject) => {
              const done = subject.topics.filter((t) => statuses.get(t.id) === 'done').length
              return (
                <Card key={subject.id}>
                  <details>
                    <summary className="flex cursor-pointer items-baseline justify-between gap-3 text-sm">
                      <span className="font-medium text-slate-900">{subject.short_name}</span>
                      <span className="text-slate-600 tabular-nums">
                        {done}/{subject.topics.length} bitti
                      </span>
                    </summary>
                    <ul className="mt-3 divide-y divide-slate-100">
                      {subject.topics.map((topic) => (
                        <li key={topic.id} className="flex items-center justify-between gap-3 py-1.5 text-sm">
                          <span className="text-slate-900">{topic.name}</span>
                          <TopicStatusBadge status={statuses.get(topic.id) ?? 'not_started'} />
                        </li>
                      ))}
                    </ul>
                  </details>
                </Card>
              )
            })}
          </div>
        </Section>
      </div>
    </DashboardLayout>
  )
}
