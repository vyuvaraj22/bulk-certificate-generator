import { Toaster } from 'react-hot-toast'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import CreateJob from './pages/CreateJob'
import Dashboard from './pages/Dashboard'
import JobDetail from './pages/JobDetail'
import JobsList from './pages/JobsList'

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--bg-card)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            fontSize: '13.5px',
          },
        }}
      />
      <div className="app-shell">
        <Sidebar />
        <Routes>
          <Route path="/"          element={<Dashboard />} />
          <Route path="/jobs"      element={<JobsList />} />
          <Route path="/jobs/:jobId" element={<JobDetail />} />
          <Route path="/create"    element={<CreateJob />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
