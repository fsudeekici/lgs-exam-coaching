import { useEffect, useState } from 'react'
import { errorMessage, fetchMyAnalytics, type StudentAnalytics } from '../api'
import DashboardLayout from '../components/DashboardLayout'
import StudentAnalyticsView from '../components/StudentAnalyticsView'

/** The student's own exam analytics: the admin's view, read only. */
export default function StudentAnalyticsPage() {
  const [data, setData] = useState<StudentAnalytics | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchMyAnalytics()
      .then(setData)
      .catch((err) => setError(errorMessage(err)))
  }, [])

  return (
    <DashboardLayout title="Deneme analizim">
      {data ? (
        <div className="-mt-8">
          <StudentAnalyticsView data={data} examLinks={false} />
        </div>
      ) : error ? (
        <p className="text-red-700">{error}</p>
      ) : (
        <p className="text-slate-500">Yükleniyor…</p>
      )}
    </DashboardLayout>
  )
}
