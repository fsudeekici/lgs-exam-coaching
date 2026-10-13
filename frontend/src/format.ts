/** LGS net score: every 3 wrong answers cancel 1 correct answer. */
export const calculateNet = (correct: number, wrong: number) => correct - wrong / 3

export const formatNet = (net: number) =>
  net.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/** Formats an ISO date (YYYY-MM-DD) as DD.MM.YYYY. */
export const formatDate = (isoDate: string) => isoDate.split('-').reverse().join('.')

/** Sorts people by name using Turkish alphabet order. */
export const byName = (a: { full_name: string }, b: { full_name: string }) =>
  a.full_name.localeCompare(b.full_name, 'tr')
