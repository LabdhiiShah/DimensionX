import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import CinzelFont from '../components/CinzelFont.jsx';
import { projectsApi, clearSession, getUser } from '../lib/api.js';

const FLOW_KEY = 'dimensionx_project_flow_v1';

function hasCompletedUpload(project) {
  try {
    const saved = JSON.parse(localStorage.getItem(FLOW_KEY) || '{}');
    return Boolean(saved[String(project.id)]?.validated);
  } catch {
    return false;
  }
}

export default function ProjectsPage() {
  const navigate = useNavigate();
  const user = getUser();
  const displayName = user?.fullName || user?.username || 'User';
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    projectsApi.list()
      .then((data) => {
        if (active) setProjects(Array.isArray(data?.projects) ? data.projects : []);
      })
      .catch((err) => {
        if (!active) return;
        if (err.status === 401) {
          navigate('/', { replace: true });
          return;
        }
        setError(err.message || 'Could not load your assigned projects.');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [navigate]);

  const logout = () => { clearSession(); navigate('/'); };
  const openProject = (project) => {
    const route = hasCompletedUpload(project) ? '/studio' : '/upload-dxf';
    navigate(route, { state: { project } });
  };
  const value = (project, camel, snake) => project[camel] ?? project[snake];
  const formatDate = (dateValue) => {
    if (!dateValue) return '';
    const date = new Date(dateValue);
    return Number.isNaN(date.getTime()) ? dateValue : date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
  };

  return (
    <div className="min-h-screen bg-white p-4 sm:p-8 font-serif">
      <CinzelFont />
      <header className="max-w-6xl mx-auto bg-[#cdeef2] rounded-full px-5 sm:px-10 py-4 flex items-center justify-between shadow-sm mb-8">
        <button type="button" onClick={() => navigate('/dashboard')} className="flex items-center gap-2 text-left" aria-label="Go to dashboard">
          <span className="text-[#800a1d] font-cinzel font-black text-2xl sm:text-3xl tracking-tighter">X</span>
          <span className="text-[#800a1d] font-cinzel font-bold text-lg sm:text-2xl tracking-widest">DIMENSIONX</span>
        </button>
        <div className="flex items-center gap-3 sm:gap-4">
          <span className="hidden sm:inline text-[#800a1d] font-sans text-sm font-semibold">{user?.username || displayName}</span>
          <button type="button" onClick={logout} className="bg-[#800a1d] text-white font-cinzel text-xs sm:text-sm tracking-widest px-5 sm:px-6 py-2.5 rounded-full hover:bg-[#600716] transition-colors">LOGOUT</button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto">
        <section className="mb-8">
          <p className="text-[#800a1d]/70 font-sans text-xs sm:text-sm tracking-[0.2em] mb-2">EMPLOYEE WORKSPACE</p>
          <h1 className="text-[#800a1d] font-cinzel font-bold text-3xl sm:text-4xl tracking-widest">WELCOME, {displayName.toUpperCase()}</h1>
          <p className="font-sans text-sm sm:text-base text-[#6b5b60] mt-3 max-w-2xl">Select a project to upload its floor plan or continue working on an existing model.</p>
        </section>

        <section className="bg-[#cdeef2] rounded-3xl p-5 sm:p-8 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2 mb-6">
            <div>
              <h2 className="text-[#800a1d] font-cinzel font-bold text-xl sm:text-2xl tracking-widest">MY ASSIGNED PROJECTS</h2>
              <p className="font-sans text-sm text-[#800a1d]/70 mt-1">Your current project list</p>
            </div>
            {!loading && !error && <span className="font-sans text-sm font-semibold text-[#800a1d]">{projects.length} {projects.length === 1 ? 'project' : 'projects'}</span>}
          </div>

          {loading ? (
            <div className="bg-white/70 rounded-2xl p-8 text-center"><p className="font-sans text-sm text-[#800a1d]/75">Loading your projects…</p></div>
          ) : error ? (
            <div role="alert" className="bg-white rounded-2xl p-6"><p className="font-sans text-sm text-[#800a1d]">{error}</p><button type="button" onClick={() => window.location.reload()} className="mt-4 bg-[#800a1d] text-white font-cinzel text-xs tracking-widest px-5 py-2.5 rounded-full hover:bg-[#600716]">TRY AGAIN</button></div>
          ) : projects.length === 0 ? (
            <div className="bg-white/70 rounded-2xl p-8 sm:p-12 text-center">
              <h3 className="text-[#800a1d] font-cinzel font-bold text-lg tracking-widest">NO PROJECTS ASSIGNED YET</h3>
              <p className="font-sans text-sm text-[#6b5b60] mt-2 max-w-md mx-auto">Projects assigned to you by an administrator will appear here.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {projects.map((project) => {
                const projectName = value(project, 'projectName', 'project_name') || 'Untitled project';
                const clientName = value(project, 'clientName', 'client_name');
                const dueDate = value(project, 'dueDate', 'due_date');
                const siteAddress = value(project, 'siteAddress', 'site_address');
                const uploaded = hasCompletedUpload(project);
                return (
                  <article key={project.id} className="flex flex-col bg-white rounded-2xl p-5 sm:p-6 shadow-sm hover:shadow-md transition-shadow border border-[#800a1d]/5">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-sans text-[10px] font-bold tracking-[0.18em] text-[#800a1d]/60 uppercase">Assigned project</p>
                        <h3 className="text-[#800a1d] font-cinzel font-bold text-lg tracking-wide mt-2 break-words">{projectName}</h3>
                      </div>
                      <span className="shrink-0 rounded-full bg-[#cdeef2] px-3 py-1 text-[10px] font-sans font-bold tracking-wider text-[#800a1d]">{uploaded ? 'PLAN ADDED' : 'ASSIGNED'}</span>
                    </div>
                    {project.description && <p className="font-sans text-sm text-[#6b5b60] mt-3">{project.description}</p>}
                    <div className="mt-5 space-y-2 font-sans text-sm">
                      {clientName && <div className="flex gap-2"><span className="text-[#800a1d]/60 min-w-16">Client</span><span className="text-[#34272b] font-medium break-words">{clientName}</span></div>}
                      {dueDate && <div className="flex gap-2"><span className="text-[#800a1d]/60 min-w-16">Due date</span><span className="text-[#34272b] font-medium">{formatDate(dueDate)}</span></div>}
                      {siteAddress && <div className="flex gap-2"><span className="text-[#800a1d]/60 min-w-16">Location</span><span className="text-[#34272b] font-medium break-words">{siteAddress}</span></div>}
                    </div>
                    <button type="button" onClick={() => openProject(project)} className="mt-6 w-full bg-[#800a1d] text-white font-cinzel font-bold text-xs tracking-[0.15em] px-5 py-3 rounded-full hover:bg-[#600716] transition-colors">{uploaded ? 'OPEN DESIGN STUDIO' : 'UPLOAD FLOOR PLAN'}</button>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
