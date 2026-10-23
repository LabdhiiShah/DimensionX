import { useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { clearSession, getUser } from '../lib/api.js';
import './UploadDxfPage.css';

const MAX_FILE_SIZE = 20 * 1024 * 1024;

export default function UploadDxfPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = getUser();
  const fileInputRef = useRef(null);
  const project = location.state?.project || null;
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  function handleFile(nextFile) {
    setError('');
    setStatus('');
    if (!nextFile) {
      setFile(null);
      return;
    }
    if (!nextFile.name.toLowerCase().endsWith('.dxf')) {
      setFile(null);
      setError('Please choose a DXF file (.dxf).');
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }
    if (nextFile.size > MAX_FILE_SIZE) {
      setFile(null);
      setError('The file is too large. Maximum file size is 20 MB.');
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }
    setFile(nextFile);
  }

  // THE FUNCTION MUST SAY ASYNC HERE
  async function continueToStudio(event) {
    event.preventDefault();
    setError('');
    setStatus('Uploading and processing DXF. This may take a few seconds...');
    
    if (!file) {
      setError('Choose a DXF floor plan before continuing.');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('dxfFile', file);
      formData.append('projectId', project?.id ?? 'temp_project');

      // Ensure your backend is running on port 4000!
      const response = await fetch('http://localhost:4000/api/dxf/upload', {
        method: 'POST',
        body: formData,
      });

      // Read as text first to prevent JSON parse crashes
      const textData = await response.text();
      let data;
      
      try {
        data = JSON.parse(textData);
      } catch (parseErr) {
        console.error('Backend returned non-JSON response:', textData);
        throw new Error(`Server returned an invalid response. Check browser console for HTML error page.`);
      }

      if (!response.ok) {
        throw new Error(data.details || data.error || 'Failed to process DXF');
      }

      setStatus('DXF processed successfully. Redirecting to studio...');
      
      navigate('/studio', {
        state: { 
          project, 
          glbUrl: data.glbUrl, 
          jsonPath: data.jsonPath 
        },
      });

    } catch (err) {
      setError(err.message);
      setStatus('');
    }
  }

  function logout() {
    clearSession();
    navigate('/');
  }

  return (
    <main className="dxf-page">
      <div className="dxf-shell">
        <header className="dxf-header">
          <button className="dxf-brand" type="button" onClick={() => navigate(user?.isAdmin ? '/admin' : '/projects')} aria-label="DimensionX home">
            <span className="dxf-brand-x">X</span><span>DIMENSIONX</span>
          </button>
          <div className="dxf-header-right">
            {user?.username && <span className="dxf-user-id">{user.username}</span>}
            <button className="dxf-logout" type="button" onClick={logout}>Logout</button>
          </div>
        </header>

        <div className="dxf-heading-row">
          <div>
            <p className="dxf-eyebrow">PROJECT WORKSPACE</p>
            <h1>Upload your floor plan</h1>
            <p className="dxf-intro">Start with a DXF plan. It will be validated before the 3D model workflow begins.</p>
          </div>
          <button className="dxf-back-button" type="button" onClick={() => navigate(user?.isAdmin ? '/admin' : '/projects')}>
            Back to projects
          </button>
        </div>

        <div className="dxf-content-grid">
          <section className="dxf-project-panel">
            <div className="dxf-panel-kicker">SELECTED PROJECT</div>
            <h2>{project?.projectName || project?.name || 'Project details'}</h2>
            <div className="dxf-project-rule" />
            <dl className="dxf-project-details">
              <div><dt>Project ID</dt><dd>{project?.id ?? project?.projectId ?? '—'}</dd></div>
              <div><dt>Client</dt><dd>{project?.clientName || '—'}</dd></div>
              <div><dt>Designer</dt><dd>{project?.designerName || user?.fullName || user?.username || '—'}</dd></div>
              <div><dt>Due date</dt><dd>{project?.dueDate ? new Date(project.dueDate).toLocaleDateString() : '—'}</dd></div>
            </dl>
          </section>

          <section className="dxf-upload-panel">
            <div className="dxf-upload-panel-head">
              <div><p className="dxf-eyebrow">FLOOR PLAN</p><h2>Upload DXF</h2></div>
              <span className="dxf-format-pill">.DXF · MAX 20 MB</span>
            </div>

            <form onSubmit={continueToStudio}>
              <input
                ref={fileInputRef}
                className="dxf-file-input"
                type="file"
                accept=".dxf,application/dxf"
                onChange={(event) => handleFile(event.target.files?.[0] || null)}
                aria-label="Choose DXF file"
              />
              <button
                className={`dxf-dropzone${file ? ' has-file' : ''}`}
                type="button"
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => {
                  event.preventDefault();
                  handleFile(event.dataTransfer.files?.[0] || null);
                }}
              >
                <span className="dxf-upload-icon" aria-hidden="true">↑</span>
                <strong>{file ? file.name : 'Choose a DXF floor plan'}</strong>
                <span>{file ? `${(file.size / (1024 * 1024)).toFixed(2)} MB · Ready to continue` : 'Click to browse or drag and drop your file here'}</span>
              </button>

              <div className="dxf-requirements">
                <h3>Before you continue</h3>
                <ul>
                  <li>File format must be <strong>.dxf</strong>.</li>
                  <li>Maximum file size is <strong>20 MB</strong>.</li>
                  <li>Keep the floor plan clean and drawn to scale where possible.</li>
                </ul>
              </div>

              {error && <p className="dxf-message dxf-message-error" role="alert">{error}</p>}
              {status && <p className="dxf-message" role="status">{status}</p>}

              <div className="dxf-actions">
                {file && <button className="dxf-clear-button" type="button" onClick={() => { setFile(null); setError(''); setStatus(''); if (fileInputRef.current) fileInputRef.current.value = ''; }}>Remove file</button>}
                <button className="dxf-submit" type="submit">Continue to 3D workspace <span aria-hidden="true">→</span></button>
              </div>
            </form>
          </section>
        </div>
      </div>
    </main>
  );
}