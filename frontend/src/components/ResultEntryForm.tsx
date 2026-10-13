import { Fragment, useState, type FormEvent } from 'react'
import type { Result, ResultInput, Subject } from '../api'
import { calculateNet, formatNet } from '../format'

interface Row {
  correct: string
  wrong: string
  blank: string
  topicIds: number[]
}

type RowState =
  | { status: 'incomplete' }
  | { status: 'error'; message: string }
  | { status: 'ok'; correct: number; wrong: number; blank: number; net: number }

/**
 * Blank is optional: left empty it is filled with the remaining questions,
 * typed in it must make correct + wrong + blank equal the question count.
 */
function evaluate(row: Row, questionCount: number): RowState {
  if (row.correct === '' || row.wrong === '') return { status: 'incomplete' }
  const correct = Number(row.correct)
  const wrong = Number(row.wrong)
  const remaining = questionCount - correct - wrong
  if (remaining < 0 || (row.blank !== '' && Number(row.blank) !== remaining)) {
    return { status: 'error', message: `Toplam ${questionCount} olmalı` }
  }
  return { status: 'ok', correct, wrong, blank: remaining, net: calculateNet(correct, wrong) }
}

const toRow = (result?: Result): Row =>
  result
    ? {
        correct: String(result.correct),
        wrong: String(result.wrong),
        blank: String(result.blank),
        topicIds: result.mistake_topic_ids,
      }
    : { correct: '', wrong: '', blank: '', topicIds: [] }

interface Props {
  subjects: Subject[]
  /** Existing results when editing a student that was already entered. */
  initial?: Result[]
  saving: boolean
  onSave: (results: ResultInput[]) => void
}

/** One student's results for all subjects. Remount (via `key`) to reset it for another student. */
export default function ResultEntryForm({ subjects, initial, saving, onSave }: Props) {
  const [rows, setRows] = useState<Record<number, Row>>(() =>
    Object.fromEntries(subjects.map((s) => [s.id, toRow(initial?.find((r) => r.subject_id === s.id))])),
  )
  const [openTopics, setOpenTopics] = useState<number | null>(null)

  const states = subjects.map((s) => evaluate(rows[s.id], s.question_count))
  const allValid = states.every((s) => s.status === 'ok')
  const totalNet = states.reduce((sum, s) => sum + (s.status === 'ok' ? s.net : 0), 0)

  const update = (subjectId: number, patch: Partial<Row>) =>
    setRows((prev) => ({ ...prev, [subjectId]: { ...prev[subjectId], ...patch } }))

  const toggleTopic = (subjectId: number, topicId: number) => {
    const current = rows[subjectId].topicIds
    update(subjectId, {
      topicIds: current.includes(topicId) ? current.filter((id) => id !== topicId) : [...current, topicId],
    })
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    const results: ResultInput[] = []
    subjects.forEach((subject, i) => {
      const state = states[i]
      if (state.status !== 'ok') return
      results.push({
        subject_id: subject.id,
        correct: state.correct,
        wrong: state.wrong,
        blank: state.blank,
        mistake_topic_ids: rows[subject.id].topicIds,
      })
    })
    if (results.length === subjects.length) onSave(results)
  }

  const numberInput = (subject: Subject, field: 'correct' | 'wrong' | 'blank', label: string, extra = {}) => (
    <input
      inputMode="numeric"
      aria-label={`${subject.name} ${label}`}
      value={rows[subject.id][field]}
      onChange={(e) => update(subject.id, { [field]: e.target.value.replace(/\D/g, '').slice(0, 2) })}
      onFocus={(e) => e.target.select()}
      className="w-16 rounded-md border border-slate-300 px-2 py-1.5 text-center tabular-nums text-slate-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
      {...extra}
    />
  )

  return (
    <form onSubmit={handleSubmit}>
      <table className="w-full max-w-3xl text-left text-sm">
        <thead className="text-slate-600">
          <tr>
            <th className="py-2 pr-4 font-medium">Ders</th>
            <th className="px-2 py-2 font-medium">Doğru</th>
            <th className="px-2 py-2 font-medium">Yanlış</th>
            <th className="px-2 py-2 font-medium">Boş</th>
            <th className="px-2 py-2 text-right font-medium">Net</th>
            <th className="py-2 pl-4 font-medium">Yanlış konular</th>
          </tr>
        </thead>
        <tbody>
          {subjects.map((subject, i) => {
            const row = rows[subject.id]
            const state = states[i]
            const isOpen = openTopics === subject.id
            return (
              <Fragment key={subject.id}>
                <tr className="border-t border-slate-100">
                  <td className="py-2 pr-4 font-medium text-slate-900">
                    {subject.name} <span className="font-normal text-slate-400">({subject.question_count})</span>
                  </td>
                  <td className="px-2 py-2">{numberInput(subject, 'correct', 'doğru', { autoFocus: i === 0 })}</td>
                  <td className="px-2 py-2">{numberInput(subject, 'wrong', 'yanlış')}</td>
                  <td className="px-2 py-2">
                    {numberInput(subject, 'blank', 'boş', {
                      placeholder: state.status === 'ok' ? String(state.blank) : '',
                    })}
                  </td>
                  <td className="px-2 py-2 text-right tabular-nums">
                    {state.status === 'ok' && <span className="font-medium text-slate-900">{formatNet(state.net)}</span>}
                    {state.status === 'error' && (
                      <span role="alert" className="text-red-600">
                        {state.message}
                      </span>
                    )}
                  </td>
                  <td className="py-2 pl-4">
                    {/* Kept out of the tab order so Tab moves straight through the number fields. */}
                    <button
                      type="button"
                      tabIndex={-1}
                      onClick={() => setOpenTopics(isOpen ? null : subject.id)}
                      className="rounded-md border border-slate-300 px-2 py-1 text-slate-700 hover:bg-slate-100"
                    >
                      {row.topicIds.length > 0 ? `${row.topicIds.length} konu seçildi` : 'Konu seç'}
                    </button>
                  </td>
                </tr>
                {isOpen && (
                  <tr>
                    <td colSpan={6} className="pb-3">
                      <div className="flex flex-wrap gap-2 rounded-md bg-slate-50 p-3">
                        {subject.topics.map((topic) => (
                          <label
                            key={topic.id}
                            className="flex cursor-pointer items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1 text-slate-700 has-checked:border-indigo-500 has-checked:bg-indigo-50 has-checked:text-indigo-800"
                          >
                            <input
                              type="checkbox"
                              tabIndex={-1}
                              checked={row.topicIds.includes(topic.id)}
                              onChange={() => toggleTopic(subject.id, topic.id)}
                            />
                            {topic.name}
                          </label>
                        ))}
                        {subject.topics.length === 0 && <span className="text-slate-500">Bu ders için konu yok.</span>}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
        <tfoot>
          <tr className="border-t border-slate-200">
            <td colSpan={4} className="py-2 pr-4 font-medium text-slate-900">
              Toplam net
            </td>
            <td className="px-2 py-2 text-right font-semibold tabular-nums text-slate-900">{formatNet(totalNet)}</td>
            <td />
          </tr>
        </tfoot>
      </table>

      <div className="mt-4 flex items-center gap-4">
        <button
          type="submit"
          disabled={!allValid || saving}
          className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {saving ? 'Kaydediliyor…' : 'Kaydet'}
        </button>
        <span className="text-sm text-slate-500">
          Boş sayısını yazmazsanız otomatik hesaplanır. Enter ile kaydedebilirsiniz.
        </span>
      </div>
    </form>
  )
}
