import type { QuestionLog, Subject, TopicProgress, TopicStatus } from './api'

interface StatusMeta {
  value: TopicStatus
  label: string
  /** Badge and selected-button colours. The label always accompanies the colour. */
  badge: string
  selected: string
}

export const TOPIC_STATUSES: StatusMeta[] = [
  { value: 'not_started', label: 'Başlamadım', badge: 'bg-slate-100 text-slate-700', selected: 'border-slate-700 bg-slate-700 text-white' },
  { value: 'studying', label: 'Çalışıyorum', badge: 'bg-blue-50 text-blue-800', selected: 'border-blue-700 bg-blue-700 text-white' },
  { value: 'done', label: 'Bitti', badge: 'bg-green-50 text-green-800', selected: 'border-green-700 bg-green-700 text-white' },
  { value: 'needs_review', label: 'Tekrar gerekli', badge: 'bg-amber-50 text-amber-900', selected: 'border-amber-700 bg-amber-700 text-white' },
]

export const STATUS_BY_VALUE = new Map(TOPIC_STATUSES.map((s) => [s.value, s]))

/** topic id -> status; topics that are not in the map are not started. */
export const progressMap = (progress: TopicProgress[]) => new Map(progress.map((p) => [p.topic_id, p.status]))

export function countByStatus(subjects: Subject[], statuses: Map<number, TopicStatus>) {
  const counts: Record<TopicStatus, number> = { not_started: 0, studying: 0, done: 0, needs_review: 0 }
  for (const subject of subjects) {
    for (const topic of subject.topics) counts[statuses.get(topic.id) ?? 'not_started'] += 1
  }
  return counts
}

export const sumLogs = (logs: QuestionLog[]) =>
  logs.reduce(
    (total, log) => ({
      solved: total.solved + log.solved,
      correct: total.correct + log.correct,
      wrong: total.wrong + log.wrong,
    }),
    { solved: 0, correct: 0, wrong: 0 },
  )
