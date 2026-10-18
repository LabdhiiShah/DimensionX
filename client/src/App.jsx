import { Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './pages/LandingPage.jsx';
import ProjectsPage from './pages/ProjectsPage.jsx';
import AdminDashboard from './pages/AdminDashboard.jsx';
import StudioPage from './pages/StudioPage.jsx';
import UploadDxfPage from './pages/UploadDxfPage.jsx';
import { getToken, getUser } from './lib/api.js';

function RequireAuth({ children }) {
  return getToken() ? children : <Navigate to="/" replace />;
}

function RequireAdmin({ children }) {
  const user = getUser();
  if (!getToken()) return <Navigate to="/" replace />;
  if (!user?.isAdmin) return <Navigate to="/projects" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/admin" element={<RequireAdmin><AdminDashboard /></RequireAdmin>} />
      <Route path="/projects" element={<RequireAuth><ProjectsPage /></RequireAuth>} />
      <Route path="/upload-dxf" element={<RequireAuth><UploadDxfPage /></RequireAuth>} />
      <Route path="/studio" element={<RequireAuth><StudioPage /></RequireAuth>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
