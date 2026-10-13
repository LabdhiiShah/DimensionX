import { Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './pages/LandingPage.jsx';
import ProjectsPage from './pages/ProjectsPage.jsx';
import StudioPage from './pages/StudioPage.jsx';
import { getToken } from './lib/api.js';

// Anyone without a login token gets sent back to the landing/login page.
function RequireAuth({ children }) {
  return getToken() ? children : <Navigate to="/" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/projects" element={<RequireAuth><ProjectsPage /></RequireAuth>} />
      <Route path="/studio" element={<RequireAuth><StudioPage /></RequireAuth>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
