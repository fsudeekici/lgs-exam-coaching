import { useEffect, useState } from 'react'
import { errorMessage, fetchMySubjects, fetchMyTopicProgress, setTopicStatus, type Subject, type TopicStatus } from '../api'
import DashboardLayout from '../components/DashboardLayout'
import { StatusCounts } from '../components/study'
import { countByStatus, progressMap, TOPIC_STATUSES } from '../study'

export default function StudentTopicsPage() {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [statuses, setStatuses] = useState<Map<number, TopicStatus> | null>(null)
  const [subjectId, setSubjectId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchMySubjects(), fetchMyTopicProgress()])
      .then(([subjectData, progress]) => {
        setSubjects(subjectData)
        setStatuses(progressMap(progress))
        setSubjectId(subjectData[0]?.id ?? null)
      })
      .catch((err) => setError(errorMessage(err)))
  }, [])

  const subject = subjects.find((s) => s.id === subjectId)

  const choose = async (topicId: number, status: TopicStatus) => {
    if (!statuses) return
    const previous = statuses.get(topicId) ?? 'not_started'
    if (previous === status) return
    // Show the change at once; put it back if saving fails.
    setStatuses((current) => new Map(current).set(topicId, status))
    setError(null)
    try {
      await setTopicStatus(topicId, status)
    } catch (err) {
      setStatuses((current) => new Map(current).set(topicId, previous))
      setError(errorMessage(err))
    }
  }

  return (
    <DashboardLayout title="Konu takibi" narrow>
      {error && (
        <p role="alert" className="mb-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      {statuses && subject && (
        <>
          <StatusCounts counts={countByStatus(subjects, statuses)} />

          <div className="mt-4 grid grid-cols-3 gap-2">
            {subjects.map((s) => {
              const done = s.topics.filter((t) => statuses.get(t.id) === 'done').length
              const active = s.id === subjectId
              return (
                <button
                  key={s.id}
                  aria-pressed={active}
                  onClick={() => setSubjectId(s.id)}
                  className={`min-h-12 rounded-md border px-2 py-1 text-sm font-medium ${
                    active ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  {s.short_name}
                  <span className={`block text-xs font-normal tabular-nums ${active ? 'text-indigo-100' : 'text-slate-500'}`}>
                    {done}/{s.topics.length} bitti
                  </span>
                </button>
              )
            })}
          </div>

          <ul className="mt-4 space-y-3">
            {subject.topics.map((topic) => {
              const current = statuses.get(topic.id) ?? 'not_started'
              return (
                <li key={topic.id} className="rounded-lg border border-slate-200 bg-white p-3">
                  <div className="font-medium text-slate-900">{topic.name}</div>
                  <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4" role="group" aria-label={topic.name}>
                    {TOPIC_STATUSES.map((status) => (
                      <button
                        key={status.value}
                        aria-pressed={current === status.value}
                        onClick={() => choose(topic.id, status.value)}
                        className={`min-h-11 rounded-md border px-2 text-sm ${
                          current === status.value
                            ? `font-semibold ${status.selected}`
                            : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-100'
                        }`}
                      >
                        {current === status.value && '✓ '}
                        {status.label}
                      </button>
                    ))}
                  </div>
                </li>
              )
            })}
          </ul>
        </>
      )}
      {!statuses && !error && <p className="text-slate-500">Yükleniyor…</p>}
    </DashboardLayout>
  )
}
