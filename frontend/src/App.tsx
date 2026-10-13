import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider'
import ProtectedRoute from './components/ProtectedRoute'
import ExamDetailPage from './pages/ExamDetailPage'
import ExamsPage from './pages/ExamsPage'
import LoginPage from './pages/LoginPage'
import ParentsPage from './pages/ParentsPage'
import ParentDashboard from './pages/ParentDashboard'
import StudentLogPage from './pages/StudentLogPage'
import StudentTopicsPage from './pages/StudentTopicsPage'
import StudentsPage from './pages/StudentsPage'

// Loaded on demand: these are the only pages that need the charting library.
const StudentDetailPage = lazy(() => import('./pages/StudentDetailPage'))
const StudentAnalyticsPage = lazy(() => import('./pages/StudentAnalyticsPage'))

const loading = <p className="p-8 text-slate-500">Yükleniyor…</p>

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute role="admin" />}>
            <Route path="/admin" element={<ExamsPage />} />
            <Route path="/admin/exams/:examId" element={<ExamDetailPage />} />
            <Route path="/admin/students" element={<StudentsPage />} />
            <Route
              path="/admin/students/:studentId"
              element={
                <Suspense fallback={loading}>
                  <StudentDetailPage />
                </Suspense>
              }
            />
            <Route path="/admin/parents" element={<ParentsPage />} />
          </Route>
          <Route element={<ProtectedRoute role="student" />}>
            <Route path="/student" element={<StudentLogPage />} />
            <Route path="/student/topics" element={<StudentTopicsPage />} />
            <Route
              path="/student/analytics"
              element={
                <Suspense fallback={loading}>
                  <StudentAnalyticsPage />
                </Suspense>
              }
            />
          </Route>
          <Route element={<ProtectedRoute role="parent" />}>
            <Route path="/parent" element={<ParentDashboard />} />
          </Route>
          {/* Anything else: the login page redirects logged-in users to their dashboard. */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
