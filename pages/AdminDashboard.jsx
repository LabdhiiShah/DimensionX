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
  const [editingId, setEditingId] = useState(null); 
  const [loading, setLoading] = useState(true);
  const [employeesLoading, setEmployeesLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  
  // NEW: State to track which row's kebab menu is open
  const [activeMenu, setActiveMenu] = useState(null);

  const [formErrors, setFormErrors] = useState({});
  const [form, setForm] = useState(EMPTY_FORM);

  // NEW: Close kebab menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setActiveMenu(null);
    window.addEventListener('click', handleClickOutside);
    return () => window.removeEventListener('click', handleClickOutside);
  }, []);

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
    setFormErrors({});
    setForm(EMPTY_FORM); 
    setEditingId(null);  
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

  async function openEditProject(project) {
    setError('');
    setFormErrors({});
    setEditingId(project.id);
    setForm({
      projectName: project.projectName || '',
      clientName: project.clientName || '',
      designerEmployeeId: project.designerEmployeeId || '',
      description: project.description || '',
      clientContact: project.clientContact || '',
      siteAddress: project.siteAddress || '',
      dueDate: project.dueDate || '',
    });
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

  async function handleDeleteProject(projectId, e) {
    e.stopPropagation(); 
    if (!window.confirm("Are you sure you want to delete this project? This cannot be undone.")) return;
    
    try {
      await projectsApi.delete(projectId);
      setProjects((current) => current.filter((p) => p.id !== projectId));
    } catch (err) {
      setError(err.message || 'Failed to delete project.');
    }
  }

  const validateForm = () => {
    const errors = {};
    if (!form.projectName.trim()) errors.projectName = 'Project name is required.';
    if (!form.clientName.trim()) errors.clientName = 'Client name is required.';
    if (!form.designerEmployeeId) errors.designerEmployeeId = 'Please select a designer.';

    if (!form.dueDate) {
      errors.dueDate = 'Due date is required.';
    } else {
      const selectedDate = new Date(form.dueDate);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      if (selectedDate < today && !editingId) { 
        errors.dueDate = 'Due date cannot be in the past.';
      }
    }

    if (!form.clientContact.trim()) {
      errors.clientContact = 'Client contact is required.';
    } else {
      const phoneRegex = /^\+?[\d\s-]{10,}$/;
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!phoneRegex.test(form.clientContact) && !emailRegex.test(form.clientContact)) {
        errors.clientContact = 'Enter a valid phone number or email.';
      }
    }

    if (!form.siteAddress.trim()) {
      errors.siteAddress = 'Site address is required.';
    }
    return errors;
  };

  async function createOrUpdateProject(event) {
    event.preventDefault();
    const errors = validateForm();
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    setError('');
    setFormErrors({});
    setSaving(true);
    
    try {
      const employee = employees.find((item) => String(item.employeeId) === String(form.designerEmployeeId));
      if (!employee) throw new Error('Please select a registered designer.');
      
      const payload = {
        ...form,
        designerName: employee.fullName || employee.employeeId,
      };

      if (editingId) {
        const result = await projectsApi.update(editingId, payload);
        setProjects((current) => current.map((p) => p.id === editingId ? result.project : p));
      } else {
        const result = await projectsApi.create(payload);
        setProjects((current) => [result.project, ...current]);
      }
      
      setShowForm(false);
      setForm(EMPTY_FORM);
      setEditingId(null);
      setFormErrors({});
    } catch (err) {
      setError(err.message || `Could not ${editingId ? 'update' : 'create'} project.`);
    } finally {
      setSaving(false);
    }
  }

  const handleInputChange = (field, value) => {
    setForm({ ...form, [field]: value });
    if (formErrors[field]) {
      setFormErrors({ ...formErrors, [field]: null });
    }
  };

  async function markAsCompleted(projectId, e) {
    e.stopPropagation(); 
    try {
      await projectsApi.updateStatus(projectId, 'completed');
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

  const getInputStyle = (field) => ({
    borderColor: formErrors[field] ? '#ff4d4f' : '#ccc',
    outline: 'none',
    boxShadow: formErrors[field] ? '0 0 0 2px rgba(255, 77, 79, 0.2)' : 'none'
  });

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
                    <th style={{ width: '50px' }}></th> {/* Empty header for kebab menu */}
                  </tr>
                </thead>
                <tbody>
                  {loading ? <tr><td colSpan="6" className="admin-empty">Loading projects...</td></tr>
                    : projects.length === 0 ? <tr><td colSpan="6" className="admin-empty">No projects yet. Click “+ Add Project” to begin.</td></tr>
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
                          
                          {/* NEW: Kebab Menu */}
                          <td style={{ position: 'relative', textAlign: 'right', paddingRight: '20px' }}>
                            <div style={{ position: 'relative', display: 'inline-block' }}>
                              <button 
                                className={`kebab-button ${activeMenu === project.id ? 'active' : ''}`}
                                onClick={(e) => { 
                                  e.stopPropagation(); 
                                  setActiveMenu(activeMenu === project.id ? null : project.id); 
                                }}
                              >
                                &#8942;
                              </button>
                              
                              {activeMenu === project.id && (
                                <div className="kebab-menu" onClick={(e) => e.stopPropagation()}>
                                  <button onClick={() => { setActiveMenu(null); openEditProject(project); }}>
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                                    Edit Project
                                  </button>
                                  <button className="delete-option" onClick={(e) => { setActiveMenu(null); handleDeleteProject(project.id, e); }}>
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                                    Delete Project
                                  </button>
                                </div>
                              )}
                            </div>
                          </td>
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
                          
                          {/* UPDATED BUTTON USING THE NEW CLASS */}
                          <button 
                            onClick={(e) => markAsCompleted(project.id, e)}
                            className="mark-completed-btn"
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

      {/* ADD / EDIT PROJECT MODAL */}
      {showForm && (
        <div className="admin-overlay" onMouseDown={() => !saving && setShowForm(false)}>
          <form className="admin-form" onSubmit={createOrUpdateProject} onMouseDown={(event) => event.stopPropagation()}>
            <button type="button" className="admin-close" onClick={() => !saving && setShowForm(false)}>×</button>
            <h2>{editingId ? 'Edit Project' : 'Add Project'}</h2>
            
            <label>
              Project Name
              <input required maxLength={200} value={form.projectName} onChange={(e) => handleInputChange('projectName', e.target.value)} style={getInputStyle('projectName')} />
              {formErrors.projectName && <span className="admin-field-error">{formErrors.projectName}</span>}
            </label>

            <label>
              Client Name
              <input required maxLength={200} value={form.clientName} onChange={(e) => handleInputChange('clientName', e.target.value)} style={getInputStyle('clientName')} />
              {formErrors.clientName && <span className="admin-field-error">{formErrors.clientName}</span>}
            </label>

            <label>
              Designer
              <select required value={form.designerEmployeeId} disabled={employeesLoading || employees.length === 0} onChange={(e) => handleInputChange('designerEmployeeId', e.target.value)} style={getInputStyle('designerEmployeeId')}>
                <option value="">{employeesLoading ? 'Loading employees…' : employees.length ? 'Select a registered employee' : 'No employees found'}</option>
                {employees.map((employee) => <option key={employee.employeeId} value={employee.employeeId}>
                  {employee.fullName || employee.employeeId}{employee.email ? ` — ${employee.email}` : ''}
                </option>)}
              </select>
              {formErrors.designerEmployeeId && <span className="admin-field-error">{formErrors.designerEmployeeId}</span>}
            </label>
            {!employeesLoading && employees.length === 0 && <p className="admin-error">No employees are available. Check the server endpoint and confirm the employee has is_admin = false and a non-empty employee_id.</p>}

            <label>
              Client Contact (Phone or Email)
              <input required maxLength={200} value={form.clientContact} onChange={(e) => handleInputChange('clientContact', e.target.value)} style={getInputStyle('clientContact')} />
              {formErrors.clientContact && <span className="admin-field-error">{formErrors.clientContact}</span>}
            </label>

            <label>
              Site Address
              <input required maxLength={300} value={form.siteAddress} onChange={(e) => handleInputChange('siteAddress', e.target.value)} style={getInputStyle('siteAddress')} />
              {formErrors.siteAddress && <span className="admin-field-error">{formErrors.siteAddress}</span>}
            </label>

            <label>
              Due Date
              <input type="date" value={form.dueDate} onChange={(e) => handleInputChange('dueDate', e.target.value)} style={getInputStyle('dueDate')} />
              {formErrors.dueDate && <span className="admin-field-error">{formErrors.dueDate}</span>}
            </label>

            <label>
              Description
              <textarea rows="3" maxLength={4000} value={form.description} onChange={(e) => handleInputChange('description', e.target.value)} />
            </label>

            <button className="admin-submit" type="submit" disabled={saving || employeesLoading || employees.length === 0}>
              {saving ? (editingId ? 'Saving…' : 'Creating…') : (editingId ? 'Save Changes' : 'Create Project')}
            </button>
          </form>
        </div>
      )}
    </main>
  );
}