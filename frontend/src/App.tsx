import { Routes, Route, Navigate } from 'react-router-dom'
import { AdminShell } from './components/layout/AdminShell'
import { JudgeShell } from './components/layout/JudgeShell'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { AdminLoginPage } from './pages/admin/AdminLoginPage'
import { AdminDashboardPage } from './pages/admin/AdminDashboardPage'
import { ProjectsPage } from './pages/admin/ProjectsPage'
import { JudgesPage } from './pages/admin/JudgesPage'
import { RubricsPage } from './pages/admin/RubricsPage'
import { ResultsPage } from './pages/admin/ResultsPage'
import { AssignmentsPage } from './pages/admin/AssignmentsPage'
import { JudgeLoginPage } from './pages/judge/JudgeLoginPage'
import { JudgeProjectListPage } from './pages/judge/JudgeProjectListPage'
import { JudgeScoringPage } from './pages/judge/JudgeScoringPage'
import { LandingPage } from './pages/LandingPage'

function App() {
  return (
    <Routes>
      {/* Admin routes */}
      <Route path="/admin/login" element={<AdminLoginPage />} />
      <Route
        path="/admin"
        element={
          <ProtectedRoute requiredRole="admin">
            <AdminShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<AdminDashboardPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="judges" element={<JudgesPage />} />
        <Route path="assignments" element={<AssignmentsPage />} />
        <Route path="rubrics" element={<RubricsPage />} />
        <Route path="results" element={<ResultsPage />} />
      </Route>

      {/* Judge routes */}
      <Route path="/judge" element={<JudgeLoginPage />} />
      <Route
        path="/judge"
        element={
          <ProtectedRoute requiredRole="judge">
            <JudgeShell />
          </ProtectedRoute>
        }
      >
        <Route path="projects" element={<JudgeProjectListPage />} />
        <Route path="projects/:projectId" element={<JudgeScoringPage />} />
      </Route>

      {/* Landing page */}
      <Route path="/" element={<LandingPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
