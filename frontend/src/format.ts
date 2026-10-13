/** LGS net score: every 3 wrong answers cancel 1 correct answer. */
export const calculateNet = (correct: number, wrong: number) => correct - wrong / 3

export const formatNet = (net: number) =>
  net.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/** Formats an ISO date (YYYY-MM-DD) as DD.MM.YYYY. */
export const formatDate = (isoDate: string) => isoDate.split('-').reverse().join('.')

/** Sorts people by name using Turkish alphabet order. */
export const byName = (a: { full_name: string }, b: { full_name: string }) =>
  a.full_name.localeCompare(b.full_name, 'tr')

/** A net difference with an explicit sign, e.g. "+1,33" or "−2,00". */
export const formatChange = (change: number) => `${change > 0 ? '+' : change < 0 ? '−' : ''}${formatNet(Math.abs(change))}`

/** Short axis label for an exam date: DD.MM */
export const formatShortDate = (isoDate: string) => isoDate.split('-').reverse().slice(0, 2).join('.')

/** A Date as YYYY-MM-DD in local time. */
export const toIsoDate = (date: Date) => date.toLocaleDateString('sv-SE')

export const daysAgo = (days: number) => {
  const date = new Date()
  date.setDate(date.getDate() - days)
  return toIsoDate(date)
}
