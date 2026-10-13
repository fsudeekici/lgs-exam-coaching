import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { errorMessage, fetchOverview, type OverviewRow } from '../api'
import DashboardLayout from '../components/DashboardLayout'
import Delta from '../components/Delta'
import { formatDate, formatNet } from '../format'

/** Admin home: every active student at a glance. */
export default function OverviewPage() {
  const [rows, setRows] = useState<OverviewRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchOverview()
      .then(setRows)
      .catch((err) => setError(errorMessage(err)))
  }, [])

  const warned = rows?.filter((row) => row.no_recent_log).length ?? 0

  return (
    <DashboardLayout title="Genel bakış">
      {error && <p className="text-red-700">{error}</p>}
      {rows && rows.length > 0 && (
        <p className="mb-3 text-sm text-slate-600">
          {rows.length} aktif öğrenci
          {warned > 0 && (
            <>
              {' · '}
              <span className="font-medium text-amber-900">⚠ {warned} öğrenci son 3 günde soru kaydı girmedi</span>
            </>
          )}
        </p>
      )}
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
            <tr>
              <th className="px-4 py-2 font-medium">Öğrenci</th>
              <th className="px-4 py-2 text-right font-medium">Son deneme neti</th>
              <th className="px-4 py-2 text-right font-medium">Önceki denemeye göre</th>
              <th className="px-4 py-2 text-right font-medium">Son 7 gün soru</th>
              <th className="px-4 py-2 text-right font-medium">Zayıf konu</th>
              <th className="px-4 py-2 font-medium">Soru kaydı</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows?.map((row) => (
              <tr key={row.student_id} className="hover:bg-slate-50">
                <td className="px-4 py-2">
                  <Link to={`/admin/students/${row.student_id}`} className="font-medium text-indigo-700 hover:underline">
                    {row.full_name}
                  </Link>
                  {row.class_name && <span className="ml-2 text-slate-500">{row.class_name}</span>}
                </td>
                <td className="px-4 py-2 text-right">
                  {row.last_exam ? (
                    <>
                      <div className="font-semibold tabular-nums text-slate-900">{formatNet(row.last_exam.total_net)}</div>
                      <div className="text-xs text-slate-500">
                        {row.last_exam.name} · {formatDate(row.last_exam.exam_date)}
                      </div>
                    </>
                  ) : (
                    <span className="text-slate-400">Deneme yok</span>
                  )}
                </td>
                <td className="px-4 py-2 text-right">
                  <Delta change={row.last_exam?.change ?? null} />
                </td>
                <td className="px-4 py-2 text-right tabular-nums text-slate-900">{row.week_solved}</td>
                <td className="px-4 py-2 text-right tabular-nums text-slate-900">{row.weak_topic_count}</td>
                <td className="px-4 py-2">
                  {row.no_recent_log ? (
                    <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-900">
                      ⚠ {row.last_log_date ? `Son 3 günde kayıt yok · son: ${formatDate(row.last_log_date)}` : 'Hiç kayıt yok'}
                    </span>
                  ) : (
                    <span className="text-slate-500">Son: {formatDate(row.last_log_date!)}</span>
                  )}
                </td>
              </tr>
            ))}
            {rows?.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                  Aktif öğrenci yok.{' '}
                  <Link to="/admin/students" className="text-indigo-700 hover:underline">
                    Öğrenci ekleyin
                  </Link>
                  .
                </td>
              </tr>
            )}
            {!rows && !error && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                  Yükleniyor…
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-slate-500">
        Zayıf konu: öğrencinin son 3 denemesinin en az 2’sinde yanlış yaptığı konu sayısı.
      </p>
    </DashboardLayout>
  )
}
