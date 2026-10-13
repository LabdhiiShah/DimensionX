import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import CinzelFont from '../components/CinzelFont.jsx';
import { projectsApi, clearSession, getUser } from '../lib/api.js';

const EMPTY = { projectName: '', description: '', clientName: '', clientContact: '', designerName: '', siteAddress: '', dueDate: '' };

const inputCls = 'w-full bg-[#cdeef2] text-[#800a1d] placeholder-[#800a1d]/50 font-sans px-5 py-3 rounded-2xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-white';
const labelCls = 'block font-sans text-xs tracking-wide mb-1.5 font-semibold';

export default function ProjectsPage() {
  const navigate = useNavigate();
  const user = getUser();
  const displayName = user?.username || 'User';
  const [form, setForm] = useState(EMPTY);
  const [projects, setProjects] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);

  const logout = () => { clearSession(); navigate('/'); };

  useEffect(() => {
    projectsApi.list()
      .then((d) => setProjects(d.projects))
      .catch((e) => {
        if (e.status === 401) return navigate('/', { replace: true });
        setError(e.message);
      })
      .finally(() => setLoadingList(false));
  }, [navigate]);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const openStudio = (project) => navigate('/studio', { state: { project } });

  async function handleCreate(e) {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      const { project } = await projectsApi.create(form);
      setProjects((p) => [project, ...p]);
      setForm(EMPTY);
      setShowForm(false);
      openStudio(project);  // straight into the design studio for the new project
    } catch (err) {
      if (err.status === 401) return navigate('/', { replace: true });
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-white p-4 sm:p-8 font-serif">
      <CinzelFont />
      <header className="max-w-6xl mx-auto bg-[#cdeef2] rounded-full px-6 sm:px-10 py-4 flex items-center justify-between shadow-sm mb-6">
        <div className="flex items-center gap-2">
          <span className="text-[#800a1d] font-cinzel font-black text-2xl sm:text-3xl tracking-tighter">X</span>
          <span className="text-[#800a1d] font-cinzel font-bold text-xl sm:text-2xl tracking-widest">DIMENSIONX</span>
        </div>
        <div className="flex items-center gap-4">
          {user?.username && <span className="hidden sm:inline text-[#800a1d] font-sans text-sm font-semibold">{user.username}</span>}
          <button onClick={logout} className="bg-[#800a1d] text-white font-cinzel text-xs sm:text-sm tracking-widest px-6 py-2.5 rounded-full hover:bg-[#600716] transition-colors cursor-pointer">LOGOUT</button>
        </div>
      </header>

      <div className="max-w-6xl mx-auto mb-6">
        <h1 className="text-[#800a1d] font-cinzel font-bold text-3xl sm:text-4xl tracking-widest">WELCOME, {displayName.toUpperCase()}</h1>
      </div>

      {showForm ? (
        <main className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-5 gap-6">
        <section className="lg:col-span-3 bg-[#800a1d] text-white rounded-3xl p-8 sm:p-10 shadow-lg">
          <h2 className="font-cinzel font-bold text-2xl sm:text-3xl tracking-widest mb-1">NEW PROJECT</h2>
          <p className="font-sans text-sm text-white/75 mb-7">Fill in the project details, then continue to the design studio.</p>

          <form onSubmit={handleCreate} className="space-y-5">
            <div>
              <label className={labelCls}>Project name *</label>
              <input className={inputCls} value={form.projectName} onChange={set('projectName')} required maxLength={200} placeholder="Sharma residence, 3BHK" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div>
                <label className={labelCls}>Client name *</label>
                <input className={inputCls} value={form.clientName} onChange={set('clientName')} required maxLength={200} />
              </div>
              <div>
                <label className={labelCls}>Client email or phone</label>
                <input className={inputCls} value={form.clientContact} onChange={set('clientContact')} maxLength={200} />
              </div>
              <div>
                <label className={labelCls}>Designer name *</label>
                <input className={inputCls} value={form.designerName} onChange={set('designerName')} required maxLength={200} />
              </div>
              <div>
                <label className={labelCls}>Due date</label>
                <input type="date" className={inputCls} value={form.dueDate} onChange={set('dueDate')} />
              </div>
            </div>
            <div>
              <label className={labelCls}>Site address</label>
              <input className={inputCls} value={form.siteAddress} onChange={set('siteAddress')} maxLength={300} />
            </div>
            <div>
              <label className={labelCls}>Description</label>
              <textarea className={`${inputCls} min-h-24 resize-y`} value={form.description} onChange={set('description')} maxLength={4000} />
            </div>

            {error && <p role="alert" className="font-sans text-sm text-[#ffd9d9]">{error}</p>}

            <button type="submit" disabled={saving} className="bg-[#cdeef2] text-[#800a1d] font-cinzel font-bold tracking-widest px-8 py-3 rounded-full hover:bg-white transition-colors cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed">
              {saving ? 'SAVING…' : 'CREATE PROJECT'}
            </button>
            <button type="button" onClick={() => { setShowForm(false); setError(''); setForm(EMPTY); }} className="ml-3 text-white font-cinzel text-sm tracking-widest underline cursor-pointer">
              CANCEL
            </button>
          </form>
        </section>

        <section className="lg:col-span-2 bg-[#cdeef2] rounded-3xl p-8 shadow-sm">
          <h2 className="text-[#800a1d] font-cinzel font-bold text-xl tracking-widest mb-5">PROJECT HISTORY</h2>
          {loadingList ? (
            <p className="font-sans text-sm text-[#800a1d]/70">Loading…</p>
          ) : projects.length === 0 ? (
            <p className="font-sans text-sm text-[#800a1d]/70">No projects yet. Create your first one with the form.</p>
          ) : (
            <ul className="space-y-3">
              {projects.map((p) => (
                <li key={p.id}>
                  <button onClick={() => openStudio(p)} className="w-full text-left bg-white rounded-2xl px-5 py-4 hover:shadow-md transition-shadow cursor-pointer">
                    <span className="block text-[#800a1d] font-sans font-bold text-sm">{p.projectName}</span>
                    <span className="block font-sans text-xs text-[#6b5b60] mt-0.5">
                      {p.clientName}{p.dueDate ? `, due ${p.dueDate}` : ''}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
        </main>
      ) : (
        <main className="max-w-6xl mx-auto">
        <section className="bg-[#cdeef2] rounded-3xl p-8 shadow-sm">
          <div className="flex items-center justify-between gap-4 mb-5">
            <h2 className="text-[#800a1d] font-cinzel font-bold text-xl tracking-widest">PROJECT HISTORY</h2>
            <button onClick={() => setShowForm(true)} className="bg-[#800a1d] text-white font-cinzel text-xs sm:text-sm tracking-widest px-6 py-2.5 rounded-full hover:bg-[#600716] transition-colors cursor-pointer">+ ADD PROJECT</button>
          </div>
          {loadingList ? (
            <p className="font-sans text-sm text-[#800a1d]/70">Loading…</p>
          ) : projects.length === 0 ? (
            <p className="font-sans text-sm text-[#800a1d]/70">No projects yet. Click ADD PROJECT to create your first one.</p>
          ) : (
            <ul className="space-y-3">
              {projects.map((p) => (
                <li key={p.id}>
                  <button onClick={() => openStudio(p)} className="w-full text-left bg-white rounded-2xl px-5 py-4 hover:shadow-md transition-shadow cursor-pointer">
                    <span className="block text-[#800a1d] font-sans font-bold text-sm">{p.projectName}</span>
                    <span className="block font-sans text-xs text-[#6b5b60] mt-0.5">
                      {p.clientName}{p.dueDate ? `, due ${p.dueDate}` : ''}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
        </main>
      )}
    </div>
  );
}