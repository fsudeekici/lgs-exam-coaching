import type { QuestionLog, Subject, TopicStatus } from '../api'
import { daysAgo, formatDate } from '../format'
import { STATUS_BY_VALUE, sumLogs, TOPIC_STATUSES } from '../study'

export function TopicStatusBadge({ status }: { status: TopicStatus }) {
  const meta = STATUS_BY_VALUE.get(status)!
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${meta.badge}`}>{meta.label}</span>
}

/** Counts per status, e.g. "Bitti 5 · Çalışıyorum 3". */
export function StatusCounts({ counts }: { counts: Record<TopicStatus, number> }) {
  return (
    <div className="flex flex-wrap gap-2">
      {TOPIC_STATUSES.map((status) => (
        <span key={status.value} className={`rounded-full px-2.5 py-1 text-xs font-medium ${status.badge}`}>
          {status.label} <span className="font-semibold tabular-nums">{counts[status.value]}</span>
        </span>
      ))}
    </div>
  )
}

export function LogTotals({ label, logs }: { label: string; logs: QuestionLog[] }) {
  const total = sumLogs(logs)
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="text-sm text-slate-600">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">
        {total.solved} <span className="text-sm font-normal text-slate-500">soru</span>
      </div>
      <div className="mt-1 text-sm text-slate-600">
        {total.correct} doğru · {total.wrong} yanlış
      </div>
    </div>
  )
}

interface LogListProps {
  /** Newest first. */
  logs: QuestionLog[]
  subjects: Subject[]
  emptyText: string
  /** Shows a delete button on each entry when given. */
  onDelete?: (log: QuestionLog) => void
}

/** Question logs grouped by day. */
export function QuestionLogList({ logs, subjects, emptyText, onDelete }: LogListProps) {
  const subjectById = new Map(subjects.map((s) => [s.id, s]))
  const topicNames = new Map(subjects.flatMap((s) => s.topics.map((t) => [t.id, t.name] as const)))
  const today = daysAgo(0)

  const days: { date: string; logs: QuestionLog[] }[] = []
  for (const log of logs) {
    if (days.at(-1)?.date !== log.log_date) days.push({ date: log.log_date, logs: [] })
    days.at(-1)!.logs.push(log)
  }

  if (logs.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500">
        {emptyText}
      </p>
    )
  }

  return (
    <div className="space-y-3">
      {days.map((day) => (
        <div key={day.date} className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <div className="flex items-baseline justify-between gap-3 border-b border-slate-200 bg-slate-50 px-3 py-2 text-sm">
            <span className="font-medium text-slate-900">
              {formatDate(day.date)}
              {day.date === today && <span className="font-normal text-slate-500"> · Bugün</span>}
            </span>
            <span className="text-slate-600 tabular-nums">{sumLogs(day.logs).solved} soru</span>
          </div>
          <ul className="divide-y divide-slate-100">
            {day.logs.map((log) => (
              <li key={log.id} className="flex items-center gap-3 px-3 py-2">
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-slate-900">
                    <span className="font-medium">{subjectById.get(log.subject_id)?.short_name}</span>
                    <span className="text-slate-500"> · {log.topic_id ? topicNames.get(log.topic_id) : 'Karışık'}</span>
                  </div>
                  <div className="text-sm text-slate-600 tabular-nums">
                    {log.solved} soru · {log.correct} doğru · {log.wrong} yanlış · {log.solved - log.correct - log.wrong} boş
                  </div>
                </div>
                {onDelete && (
                  <button
                    onClick={() => onDelete(log)}
                    aria-label="Kaydı sil"
                    className="h-11 w-11 shrink-0 rounded-md text-xl text-slate-400 hover:bg-slate-100 hover:text-red-600"
                  >
                    ×
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}
