import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectsApi, employeesApi, clearSession, getUser } from '../lib/api.js';
import { getUrgentProjects, getDeadlineStatus, isOverdue } from '../lib/deadlines.js';
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

  // --- NEW: Handle marking a project as completed ---
  async function markAsCompleted(projectId, e) {
    e.stopPropagation(); // Prevent the row click from opening the project
    try {
      const result = await projectsApi.updateStatus(projectId, 'completed');
      // Update local state instantly so the UI reflects the change
      setProjects((current) => 
        current.map((p) => p.id === projectId ? { ...p, status: 'completed' } : p)
      );
    } catch (err) {
      setError('Failed to mark project as completed.');
    }
  }

  function logout() {
    clearSession();
    navigate('/');
  }

  const urgentProjects = getUrgentProjects(projects);

  return (
    <main className="admin-page">
      <div className="admin-shell">
        <aside className="admin-sidebar">
          <div className="admin-logo"><span className="admin-logo-x">X</span><span>DIMENSIONX</span></div>
          <nav className="admin-navigation">
            {[['projects', 'Projects'], ['designers', 'Designers'], ['notifications', 'Notifications']].map(([id, label]) => (
              <button key={id} className={section === id ? 'selected' : ''} onClick={() => setSection(id)}>
                {label}
                {id === 'notifications' && urgentProjects.length > 0 && (
                  <span style={{ marginLeft: '8px', background: '#b31b2c', color: 'white', borderRadius: '12px', padding: '2px 8px', fontSize: '12px' }}>
                    {urgentProjects.length}
                  </span>
                )}
              </button>
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

          {/* PROJECTS TAB */}
          {section === 'projects' && (
            <section className="admin-table-card"><div className="admin-table-scroll">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Project ID</th>
                    <th>Project Name</th>
                    <th>Due Date</th>
                    <th>Status</th>
                    <th>Designer</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? <tr><td colSpan="5" className="admin-empty">Loading projects...</td></tr>
                    : projects.length === 0 ? <tr><td colSpan="5" className="admin-empty">No projects yet. Click “+ Add Project” to begin.</td></tr>
                    : projects.map((project) => {
                      const overdue = isOverdue(project.dueDate);
                      return (
                        <tr key={project.id} onClick={() => openProject(project)}>
                          <td>{project.id}</td>
                          <td>{project.projectName}</td>
                          <td style={{ color: overdue ? '#d9534f' : 'inherit', fontWeight: overdue ? 'bold' : 'normal' }}>
                            {project.dueDate ? new Date(project.dueDate).toLocaleDateString() : '—'}
                          </td>
                          <td style={{ textTransform: 'capitalize', color: project.status === 'completed' ? '#28a745' : '#666', fontWeight: 'bold' }}>
                            {project.status || 'active'}
                          </td>
                          <td>{project.designerName || '—'}</td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div></section>
          )}

          {/* DESIGNERS TAB */}
          {section === 'designers' && (
            <section className="admin-table-card">
              <h2>Registered Employees</h2>
              {employeesLoading ? <p className="admin-empty">Loading employees...</p>
                : employees.length === 0 ? <p className="admin-empty">No registered non-admin employees were returned by the server.</p>
                : <div className="admin-table-scroll"><table className="admin-table"><thead><tr><th>Employee ID</th><th>Name</th><th>Email</th></tr></thead>
                  <tbody>{employees.map((employee) => <tr key={employee.employeeId}><td>{employee.employeeId}</td><td>{employee.fullName || '—'}</td><td>{employee.email || '—'}</td></tr>)}</tbody></table></div>}
            </section>
          )}

          {/* NOTIFICATIONS TAB */}
          {section === 'notifications' && (
            <section className="admin-table-card" style={{ padding: '24px' }}>
              <h2>Deadline Reminders</h2>
              {urgentProjects.length === 0 ? (
                <p className="admin-empty" style={{ marginTop: '16px' }}>No upcoming or overdue deadlines right now. You're all caught up!</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '16px' }}>
                  {urgentProjects.map((project) => {
                    const status = getDeadlineStatus(project.dueDate);
                    
                    return (
                      <div key={project.id} style={{
                        border: '1px solid #ddd', borderRadius: '8px', padding: '16px',
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        backgroundColor: '#fafafa'
                      }}>
                        <div>
                          <h3 style={{ margin: '0 0 8px 0', color: '#333' }}>{project.projectName}</h3>
                          <p style={{ margin: 0, color: '#666', fontSize: '14px' }}>
                            <strong>Client:</strong> {project.clientName} &nbsp;|&nbsp; 
                            <strong>Designer:</strong> {project.designerName} &nbsp;|&nbsp; 
                            <strong>Deadline:</strong> {new Date(project.dueDate).toLocaleDateString()}
                          </p>
                        </div>
                        
                        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                          <span style={{
                            backgroundColor: status.color, color: 'white', padding: '6px 12px',
                            borderRadius: '20px', fontSize: '13px', fontWeight: 'bold', whiteSpace: 'nowrap'
                          }}>
                            {status.text}
                          </span>
                          
                          {/* NEW BUTTON TO MARK AS COMPLETED */}
                          <button 
                            onClick={(e) => markAsCompleted(project.id, e)}
                            style={{
                              backgroundColor: '#28a745', color: 'white', border: 'none',
                              padding: '8px 12px', borderRadius: '6px', cursor: 'pointer',
                              fontSize: '13px', fontWeight: 'bold'
                            }}
                          >
                            Mark Completed
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          )}
        </section>
      </div>

      {/* ADD PROJECT MODAL */}
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