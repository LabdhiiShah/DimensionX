import React, { useState } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';

// Landing / Login Page Component
function LandingPage() {
  const [showLogin, setShowLogin] = useState(false);
  const [employeeId, setEmployeeId] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleLoginSubmit = (e) => {
    e.preventDefault();
// Extract username prefix before '@' (e.g., 'admin' from 'admin@dimensions')
    const username = employeeId.includes('@') ? employeeId.split('@')[0] : employeeId;

    // Check if the user is an admin (e.g., employeeId includes 'admin')
    const isAdmin = employeeId.toLowerCase().includes('admin');

    // Redirect to dashboard with state
    navigate('/dashboard', { state: { username, isAdmin } });
  };

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center p-4 sm:p-8 font-serif">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800;900&display=swap');
        .font-cinzel { font-family: 'Cinzel', serif; }
      `}</style>

      {/* HEADER / NAVBAR */}
      <header className="w-full max-w-8xl bg-[#cdeef2] rounded-full px-6 sm:px-10 py-4 flex items-center justify-between shadow-sm mb-6">
        <div className="flex items-center gap-2">
          <span className="text-[#800a1d] font-cinzel font-black text-2xl sm:text-3xl tracking-tighter">X</span>
          <span className="text-[#800a1d] font-cinzel font-bold text-xl sm:text-2xl tracking-widest">DIMENSIONX</span>
        </div>

        {!showLogin && (
          <button
            onClick={() => setShowLogin(true)}
            className="bg-[#800a1d] text-white font-cinzel text-xs sm:text-sm tracking-widest px-6 py-2.5 rounded-full hover:bg-[#600716] transition-colors cursor-pointer"
          >
            GET STARTED
          </button>
        )}
      </header>

      {/* MAIN CONTAINER */}
      <main className="w-full max-w-8xl bg-[#cdeef2] rounded-3xl p-8 sm:p-12 md:p-16 min-h-[500px] flex items-center justify-center transition-all duration-500 ease-in-out shadow-sm">
        {!showLogin ? (
          /* INITIAL VIEW */
          <div className="text-center max-w-3xl flex flex-col items-center justify-center space-y-6">
            <h1 className="text-[#800a1d] font-cinzel font-bold text-3xl sm:text-4xl md:text-5xl tracking-wider">
              WELCOME USER
            </h1>
            <p className="text-[#800a1d] font-cinzel font-semibold text-lg sm:text-2xl md:text-3xl leading-relaxed tracking-wide uppercase">
              TRANSFORM 2D ARCHITECTURAL PLANS INTO INTERACTIVE LIVING ENVIRONMENTS
            </p>
            <button
              onClick={() => setShowLogin(true)}
              className="mt-4 bg-[#800a1d] text-white font-cinzel font-bold text-sm sm:text-base tracking-widest px-8 py-3 rounded-full hover:bg-[#600716] transition-all transform hover:scale-105 shadow-md cursor-pointer"
            >
              GET STARTED
            </button>
          </div>
        ) : (
          /* LOGIN VIEW */
          <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
            
            <div className="flex flex-col justify-center text-center md:text-left pr-0 md:pr-6 space-y-4">
              <h1 className="text-[#800a1d] font-cinzel font-bold text-3xl sm:text-4xl lg:text-5xl tracking-wider">
                WELCOME USER
              </h1>
              <p className="text-[#800a1d] font-cinzel font-semibold text-lg sm:text-xl lg:text-2xl leading-relaxed tracking-wide uppercase">
                TRANSFORM 2D ARCHITECTURAL PLANS INTO INTERACTIVE LIVING ENVIRONMENTS
              </p>
            </div>

            <div className="bg-[#800a1d] text-white rounded-3xl p-8 sm:p-10 shadow-lg flex flex-col justify-center">
              <h2 className="text-center font-cinzel font-bold text-2xl sm:text-3xl tracking-widest mb-8">
                LOGIN
              </h2>

              <form onSubmit={handleLoginSubmit} className="space-y-6">
                <div>
                  <label className="block font-sans text-xs sm:text-sm tracking-wider mb-2 font-semibold uppercase">
                    EMPLOYEE/ADMIN ID
                  </label>
                  <input
                    type="text"
                    placeholder="name@dimensions"
                    value={employeeId}
                    onChange={(e) => setEmployeeId(e.target.value)}
                    required
                    className="w-full bg-[#cdeef2] text-[#800a1d] placeholder-[#800a1d]/60 font-sans px-6 py-3.5 rounded-full text-sm font-medium focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block font-cinzel text-xs sm:text-sm tracking-wider mb-2 font-semibold uppercase">
                    PASSWORD
                  </label>
                  <input
                    type="password"
                    placeholder="••••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full bg-[#cdeef2] text-[#800a1d] placeholder-[#800a1d]/60 font-sans px-6 py-3.5 rounded-full text-sm font-medium focus:outline-none"
                  />
                </div>

                <div className="pt-2">
                  <button
                    type="submit"
                    className="w-full bg-[#cdeef2] text-[#800a1d] font-cinzel font-bold tracking-widest py-3 rounded-full hover:bg-white transition-colors cursor-pointer"
                  >
                    SUBMIT
                  </button>
                </div>
              </form>

              <button
                onClick={() => setShowLogin(false)}
                className="mt-4 text-center font-cinzel text-xs text-white/80 hover:text-white underline tracking-widest cursor-pointer"
              >
                ← BACK
              </button>
            </div>

          </div>
        )}
      </main>
    </div>
  );
}

// Root App Router
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/dashboard" element={<Dashboard />} />
    </Routes>
  );
}