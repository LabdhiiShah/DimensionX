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
  const [loading, setLoading] = useState(false);

  // Check if the project already has a generated model
  const isAlreadyUploaded = Boolean(project?.glb_url || project?.dxf_file_path);

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

  async function continueToStudio(event) {
    event.preventDefault();
    
    if (!file) {
      setError('Choose a DXF floor plan before continuing.');
      return;
    }

    setError('');
    setStatus('Uploading and processing DXF. This may take a few seconds...');
    setLoading(true);
    
    try {
      const formData = new FormData();
      formData.append('projectId', project?.id ?? project?.projectId ?? 'temp_project'); 
      formData.append('dxfFile', file); 

      const response = await fetch('http://localhost:4000/api/dxf/upload', {
        method: 'POST',
        body: formData,
      });

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
    } finally {
      setLoading(false);
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

            {/* Show VIEW HOUSE button if already uploaded */}
            {isAlreadyUploaded ? (
              <div className="flex flex-col items-center justify-center py-12 text-center px-4 h-full">
                <div className="w-16 h-16 bg-[#cdeef2] rounded-full flex items-center justify-center mb-4 text-[#800a1d]">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-8 h-8">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
                  </svg>
                </div>
                <h3 className="text-[#800a1d] font-cinzel font-bold text-xl mb-2">House Already Generated</h3>
                <p className="text-gray-500 font-sans text-sm mb-8">A 3D model already exists for this project.</p>
                
                <button
                  onClick={() => navigate('/studio', { state: { project, glbUrl: project.glb_url, plan: project.plan } })}
                  className="dxf-submit"
                  style={{ padding: '12px 32px', fontSize: '13px' }}
                >
                  VIEW HOUSE <span aria-hidden="true">→</span>
                </button>
              </div>
            ) : (
              // Otherwise, show the upload form
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
                  {file && !loading && (
                    <button 
                      className="dxf-clear-button" 
                      type="button" 
                      onClick={() => { 
                        setFile(null); 
                        setError(''); 
                        setStatus(''); 
                        if (fileInputRef.current) fileInputRef.current.value = ''; 
                      }}
                    >
                      Remove file
                    </button>
                  )}
                  <button 
                    className="dxf-submit" 
                    type="submit" 
                    disabled={loading || !file}
                    style={{ opacity: (loading || !file) ? 0.6 : 1, cursor: (loading || !file) ? 'not-allowed' : 'pointer' }}
                  >
                    {loading ? 'Processing...' : 'Continue to 3D workspace'} <span aria-hidden="true">→</span>
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}