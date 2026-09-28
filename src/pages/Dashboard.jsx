import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export default function Dashboard() {
  const navigate = useNavigate();
  const location = useLocation();

  // Get User Details from login state
  const username = location.state?.username || 'User';
  const isAdmin = location.state?.isAdmin ?? true; // Default to true if accessed directly

  // Modal State
  const [showAddProjectModal, setShowAddProjectModal] = useState(false);

  // Form Fields State
  const [projectName, setProjectName] = useState('');
  const [selectedDesigner, setSelectedDesigner] = useState('');
  const [clientName, setClientName] = useState('');
  const [projectLocation, setProjectLocation] = useState('');

  // Sample Designer List
  const designers = [
    'Add Designer 1',
    'Add Designer 2',
    'Add Designer 3',
    'Bhoomi Desai',
    'Ar. Sharma'
  ];

  const handleLogout = () => {
    navigate('/');
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    alert(`Project "${projectName}" created successfully!`);
    
    // Reset Form and Close Modal
    setProjectName('');
    setSelectedDesigner('');
    setClientName('');
    setProjectLocation('');
    setShowAddProjectModal(false);
  };

  return (
    <div className="min-h-screen bg-white p-6 flex gap-6 font-serif select-none relative">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800;900&display=swap');
        .font-cinzel { font-family: 'Cinzel', serif; }
      `}</style>

      {/* LEFT SIDEBAR */}
      <aside className="w-64 bg-[#cdeef2] rounded-3xl p-6 flex flex-col justify-between shadow-sm min-h-[calc(100vh-3rem)]">
        <div>
          <div className="flex items-center gap-1 cursor-pointer">
            <span className="font-cinzel font-black text-3xl text-[#800a1d] tracking-tighter">
              X
            </span>
            <span className="font-cinzel font-bold text-xl text-[#800a1d] tracking-widest uppercase">
              DIMENSIONX
            </span>
          </div>
        </div>

        <div>
          <button
            onClick={handleLogout}
            className="text-[#800a1d] font-sans font-bold text-base  tracking-wider transition-all cursor-pointer"
          >
            Logout 
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 flex flex-col gap-6">
        
        {/* TOP HEADER */}
        <header className="flex items-center justify-between py-2">
          <h1 className="text-[#800a1d] font-cinzel font-bold text-3xl sm:text-4xl tracking-wide capitalize">
            Welcome {username}!
          </h1>

          {/* "+ Add Project" Button ONLY visible for Admins */}
          {isAdmin && (
            <button
              onClick={() => setShowAddProjectModal(true)}
              className="bg-[#cdeef2] hover:bg-[#bce6eb] text-[#800a1d] font-cinzel font-bold text-sm tracking-wider px-6 py-3 rounded-full transition-all shadow-sm cursor-pointer"
            >
              + Add Project
            </button>
          )}
        </header>

    

      </main>

      {/* ================= ADD PROJECT POPUP MODAL ================= */}
      {showAddProjectModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="w-full max-w-md bg-[#cdeef2] rounded-3xl p-8 shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            
            {/* Close Button */}
            <button
              onClick={() => setShowAddProjectModal(false)}
              className="absolute top-6 right-6 text-[#800a1d] font-bold text-xl hover:opacity-70 cursor-pointer"
            >
              ✕
            </button>

            {/* Logo */}
            <div className="flex items-center justify-center gap-1 mb-8">
              <span className="font-cinzel font-black text-3xl text-[#800a1d] tracking-tighter">X</span>
              <span className="font-cinzel font-bold text-2xl text-[#800a1d] tracking-widest uppercase">DIMENSIONX</span>
            </div>

            {/* Form */}
            <form onSubmit={handleFormSubmit} className="space-y-4">
              
              {/* Enter Project Name */}
              <div>
                <input
                  type="text"
                  placeholder="Enter Project Name"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  required
                  className="w-full bg-white text-[#800a1d] placeholder-[#b4b4b4] font-sans  text-sm px-6 py-4 rounded-2xl shadow-xs focus:outline-none"
                />
              </div>

              {/* Add Designer (Dropdown Menu) */}
              <div>
                <select
                  value={selectedDesigner}
                  onChange={(e) => setSelectedDesigner(e.target.value)}
                  required
                  className="w-full bg-white text-[#b4b4b4] font-sans  text-sm px-6 py-4 rounded-2xl shadow-xs focus:outline-none cursor-pointer appearance-none bg-[url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23800a1d%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E')] bg-[length:12px_12px] bg-[right_24px_center] bg-no-repeat"
                >
                  <option value="" disabled hidden>Add Designer</option>
                  {designers.map((designer, idx) => (
                    <option key={idx} value={designer} className="text-[#800a1d] font-sans py-2">
                      {designer}
                    </option>
                  ))}
                </select>
              </div>

              {/* Enter Client Name */}
              <div>
                <input
                  type="text"
                  placeholder="Enter Client Name"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  required
                  className="w-full bg-white text-[#800a1d] placeholder-[#b4b4b4] font-sans text-sm px-6 py-4 rounded-2xl shadow-xs focus:outline-none"
                />
              </div>

              {/* Enter Location */}
              <div>
                <input
                  type="text"
                  placeholder="Enter Location"
                  value={projectLocation}
                  onChange={(e) => setProjectLocation(e.target.value)}
                  required
                  className="w-full bg-white text-[#800a1d] placeholder-[#b4b4b4] font-sans text-sm px-6 py-4 rounded-2xl shadow-xs focus:outline-none"
                />
              </div>

              {/* Submit Button */}
              <div className="pt-4 flex justify-center">
                <button
                  type="submit"
                  className="bg-white text-[#800a1d] font-sans text-sm tracking-widest px-8 py-3.5 rounded-full hover:bg-[#800a1d] hover:text-white transition-colors shadow-xs cursor-pointer"
                >
                  ADD PROJECT
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

    </div>
  );
}