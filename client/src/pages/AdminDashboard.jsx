import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectsApi, employeesApi, clearSession, getUser } from '../lib/api.js';
import './AdminDashboard.css';

const EMPTY_FORM = {
  projectName: '', clientName: '', designerEmployeeId: '', description: '',
  clientContact: '', siteAddress: '', dueDate: '',
};

export default function AdminDashboard() {
  const navigate = useNavigate();
  const user = getUser();
    const openProject = (project) => {
    let done = false;

    try {
      const saved = JSON.parse(
        localStorage.getItem('dimensionx_project_flow_v1') || '{}'
      );

      done = Boolean(saved[String(project.id)]?.validated);
    } catch {
      done = false;
    }

    navigate(done ? '/studio' : '/upload-dxf', {
      state: { project },
    });
  };
  const [projects, setProjects] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [section, setSection] = useState('projects');
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [employeesLoading, setEmployeesLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState(EMPTY_FORM);

  useEffect(() => {
    projectsApi.list()
      .then((data) => setProjects(data.projects || []))
      .catch((err) => setError(err.message || 'Could not load projects.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (section !== 'designers') return;
    employeesApi.list()
      .then((data) => setEmployees(data.employees || []))
      .catch((err) => setError(err.message || 'Could not load employees.'))
      .finally(() => setEmployeesLoading(false));
  }, [section]);

  async function openAddProject() {
    setError('');
    setEmployeesLoading(true);
    setShowForm(true);
    try {
      const data = await employeesApi.list();
      setEmployees(data.employees || []);
    } catch (err) {
      setError(err.message || 'Could not load registered employees.');
    } finally {
      setEmployeesLoading(false);
    }
  }

  async function createProject(event) {
    event.preventDefault();
    setError('');
    setSaving(true);
    try {
      const employee = employees.find((item) => String(item.employeeId) === String(form.designerEmployeeId));
      if (!employee) throw new Error('Please select a registered designer.');
      const result = await projectsApi.create({
        ...form,
        designerName: employee.fullName || employee.employeeId,
      });
      setProjects((current) => [result.project, ...current]);
      setShowForm(false);
      setForm(EMPTY_FORM);
    } catch (err) {
      setError(err.message || 'Could not create project.');
    } finally {
      setSaving(false);
    }
  }

  function logout() {
    clearSession();
    navigate('/');
  }

  return (
    <main className="admin-page">
      <div className="admin-shell">
        <aside className="admin-sidebar">
          <div className="admin-logo"><span className="admin-logo-x">X</span><span>DIMENSIONX</span></div>
          <nav className="admin-navigation">
            {[['projects', 'Projects'], ['designers', 'Designers'], ['notifications', 'Notifications']].map(([id, label]) => (
              <button key={id} className={section === id ? 'selected' : ''} onClick={() => setSection(id)}>{label}</button>
            ))}
          </nav>
          <button className="admin-logout" onClick={logout}>Logout</button>
        </aside>

        <section className="admin-content">
          <header className="admin-topbar">
            <div><h1>Welcome admin!</h1>{user?.fullName && <p className="admin-subtitle">{user.fullName}</p>}</div>
            {section === 'projects' && <button className="admin-add-button" onClick={openAddProject}>+ Add Project</button>}
          </header>

          {error && <p className="admin-error" role="alert">{error}</p>}

          {section === 'projects' && (
            <section className="admin-table-card"><div className="admin-table-scroll">
              <table className="admin-table"><thead><tr><th>Project ID</th><th>Project Name</th><th>Date Created</th><th>Designer</th></tr></thead>
                <tbody>{loading ? <tr><td colSpan="4" className="admin-empty">Loading projects...</td></tr>
                  : projects.length === 0 ? <tr><td colSpan="4" className="admin-empty">No projects yet. Click “+ Add Project” to begin.</td></tr>
                  : projects.map((project) => <tr key={project.id} onClick={() => openProject(project)}>
                    <td>{project.id}</td><td>{project.projectName}</td><td>{project.createdAt ? new Date(project.createdAt).toLocaleDateString() : '—'}</td><td>{project.designerName || '—'}</td>
                  </tr>)}</tbody>
              </table>
            </div></section>
          )}

          {section === 'designers' && (
            <section className="admin-table-card">
              <h2>Registered Employees</h2>
              {employeesLoading ? <p className="admin-empty">Loading employees...</p>
                : employees.length === 0 ? <p className="admin-empty">No registered non-admin employees were returned by the server.</p>
                : <div className="admin-table-scroll"><table className="admin-table"><thead><tr><th>Employee ID</th><th>Name</th><th>Email</th></tr></thead>
                  <tbody>{employees.map((employee) => <tr key={employee.employeeId}><td>{employee.employeeId}</td><td>{employee.fullName || '—'}</td><td>{employee.email || '—'}</td></tr>)}</tbody></table></div>}
            </section>
          )}

          {section === 'notifications' && <section className="admin-placeholder"><h2>Notifications</h2><p>No new notifications.</p></section>}
        </section>
      </div>

      {showForm && (
        <div className="admin-overlay" onMouseDown={() => !saving && setShowForm(false)}>
          <form className="admin-form" onSubmit={createProject} onMouseDown={(event) => event.stopPropagation()}>
            <button type="button" className="admin-close" onClick={() => !saving && setShowForm(false)}>×</button>
            <h2>Add Project</h2>
            <label>Project Name<input required maxLength={200} value={form.projectName} onChange={(e) => setForm({ ...form, projectName: e.target.value })} /></label>
            <label>Client Name<input required maxLength={200} value={form.clientName} onChange={(e) => setForm({ ...form, clientName: e.target.value })} /></label>
            <label>Designer
              <select required value={form.designerEmployeeId} disabled={employeesLoading || employees.length === 0}
                onChange={(e) => setForm({ ...form, designerEmployeeId: e.target.value })}>
                <option value="">{employeesLoading ? 'Loading employees…' : employees.length ? 'Select a registered employee' : 'No employees found'}</option>
                {employees.map((employee) => <option key={employee.employeeId} value={employee.employeeId}>
                  {employee.fullName || employee.employeeId}{employee.email ? ` — ${employee.email}` : ''}
                </option>)}
              </select>
            </label>
            {!employeesLoading && employees.length === 0 && <p className="admin-error">No employees are available. Check the server endpoint and confirm the employee has is_admin = false and a non-empty employee_id.</p>}
            <label>Client Contact<input maxLength={200} value={form.clientContact} onChange={(e) => setForm({ ...form, clientContact: e.target.value })} /></label>
            <label>Site Address<input maxLength={300} value={form.siteAddress} onChange={(e) => setForm({ ...form, siteAddress: e.target.value })} /></label>
            <label>Due Date<input type="date" value={form.dueDate} onChange={(e) => setForm({ ...form, dueDate: e.target.value })} /></label>
            <label>Description<textarea rows="3" maxLength={4000} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
            <button className="admin-submit" type="submit" disabled={saving || employeesLoading || employees.length === 0}>{saving ? 'Creating…' : 'Create Project'}</button>
          </form>
        </div>
      )}
    </main>
  );
}
