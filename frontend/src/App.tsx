import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider'
import ProtectedRoute from './components/ProtectedRoute'
import AccountPage from './pages/AccountPage'
import ExamDetailPage from './pages/ExamDetailPage'
import ExamsPage from './pages/ExamsPage'
import KvkkPage from './pages/KvkkPage'
import LoginPage from './pages/LoginPage'
import OverviewPage from './pages/OverviewPage'
import ParentsPage from './pages/ParentsPage'
import StudentLogPage from './pages/StudentLogPage'
import StudentTopicsPage from './pages/StudentTopicsPage'
import StudentsPage from './pages/StudentsPage'

// Loaded on demand: these are the only pages that need the charting library.
const StudentDetailPage = lazy(() => import('./pages/StudentDetailPage'))
const MeetingPage = lazy(() => import('./pages/MeetingPage'))
const StudentAnalyticsPage = lazy(() => import('./pages/StudentAnalyticsPage'))
const ParentHomePage = lazy(() => import('./pages/ParentHomePage'))

const loading = <p className="p-8 text-slate-500">Yükleniyor…</p>

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/kvkk" element={<KvkkPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/account" element={<AccountPage />} />
          </Route>
          <Route element={<ProtectedRoute role="admin" />}>
            <Route path="/admin" element={<OverviewPage />} />
            <Route path="/admin/exams" element={<ExamsPage />} />
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
            <Route
              path="/admin/students/:studentId/meeting"
              element={
                <Suspense fallback={loading}>
                  <MeetingPage />
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
            <Route
              path="/parent"
              element={
                <Suspense fallback={loading}>
                  <ParentHomePage />
                </Suspense>
              }
            />
          </Route>
          {/* Anything else: the login page redirects logged-in users to their dashboard. */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
