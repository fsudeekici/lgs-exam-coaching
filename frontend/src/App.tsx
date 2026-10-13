import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider'
import ProtectedRoute from './components/ProtectedRoute'
import ExamDetailPage from './pages/ExamDetailPage'
import ExamsPage from './pages/ExamsPage'
import LoginPage from './pages/LoginPage'
import ParentsPage from './pages/ParentsPage'
import ParentDashboard from './pages/ParentDashboard'
import StudentDashboard from './pages/StudentDashboard'
import StudentsPage from './pages/StudentsPage'

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
            <Route path="/admin/parents" element={<ParentsPage />} />
          </Route>
          <Route element={<ProtectedRoute role="student" />}>
            <Route path="/student" element={<StudentDashboard />} />
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
