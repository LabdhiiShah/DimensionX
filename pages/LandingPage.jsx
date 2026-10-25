import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import CinzelFont from '../components/CinzelFont.jsx';
import { authApi, saveSession } from '../lib/api.js';

export default function LandingPage() {
  const [mode, setMode] = useState('login'); // 'login' or 'signup'

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [employeeId, setEmployeeId] = useState('');
  const [password, setPassword] = useState('');

  const [showPassword, setShowPassword] = useState(false); // For eye icon
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState(''); 
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');
    setLoading(true);

    try {
      if (mode === 'signup') {
        await authApi.signup(
          fullName.trim(),
          email.trim(),
          employeeId.trim(),
          password
        );

        setMode('login');
        setSuccessMsg('Account created successfully! Please log in.');
        setFullName('');
        setEmail('');
        setPassword('');
      } else {
        const data = await authApi.login(employeeId.trim(), password);
        saveSession(data);
        navigate(data.isAdmin ? '/admin' : '/projects');
      }
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setMode((current) => (current === 'login' ? 'signup' : 'login'));
    setError('');
    setSuccessMsg('');
    setPassword('');
    setShowPassword(false);
  };

  const inputClass =
    'w-full bg-[#cdeef2] text-[#800a1d] placeholder-[#800a1d]/60 ' +
    'font-sans px-6 py-3.5 rounded-full text-sm font-medium focus:outline-none ' +
    'focus:ring-2 focus:ring-white';

  const labelClass =
    'block font-sans text-xs sm:text-sm tracking-wider mb-2 ' +
    'font-semibold uppercase';

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center p-4 sm:p-8 font-serif">
      <CinzelFont />

      <header className="w-full max-w-8xl bg-[#cdeef2] rounded-full px-6 sm:px-10 py-4 flex items-center justify-between shadow-sm mb-6">
        <div className="flex items-center gap-2">
          <span className="text-[#800a1d] font-cinzel font-black text-2xl sm:text-3xl tracking-tighter">
            X
          </span>
          <span className="text-[#800a1d] font-cinzel font-bold text-xl sm:text-2xl tracking-widest">
            DIMENSIONX
          </span>
        </div>
      </header>

      <main className="w-full max-w-8xl bg-[#cdeef2] rounded-3xl p-8 sm:p-12 md:p-16 min-h-[500px] flex items-center justify-center shadow-sm">
        <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
          <div className="flex flex-col justify-center text-center md:text-left pr-0 md:pr-6 space-y-4">
            <h1 className="text-[#800a1d] font-cinzel font-bold text-3xl sm:text-4xl lg:text-5xl tracking-wider">
              WELCOME TO DIMENSIONX
            </h1>
            <p className="text-[#800a1d] font-cinzel font-semibold text-lg sm:text-xl lg:text-2xl leading-relaxed tracking-wide uppercase">
              TRANSFORM 2D ARCHITECTURAL PLANS INTO INTERACTIVE LIVING ENVIRONMENTS
            </p>
          </div>

          <div className="bg-[#800a1d] text-white rounded-3xl p-8 sm:p-10 shadow-lg flex flex-col justify-center">
            <h2 className="text-center font-cinzel font-bold text-2xl sm:text-3xl tracking-widest mb-8">
              {mode === 'signup' ? 'CREATE ACCOUNT' : 'LOGIN'}
            </h2>

            <form onSubmit={handleAuthSubmit} className="space-y-5">
              {mode === 'signup' && (
                <>
                  <div>
                    <label className={labelClass}>FULL NAME</label>
                    <input
                      type="text"
                      placeholder="Enter your full name"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      autoComplete="name"
                      maxLength={120}
                      required
                      className={inputClass}
                    />
                  </div>

                  <div>
                    <label className={labelClass}>EMAIL ADDRESS</label>
                    <input
                      type="email"
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoComplete="email"
                      maxLength={254}
                      required
                      className={inputClass}
                    />
                  </div>
                </>
              )}

              <div>
                <label className={labelClass}>EMPLOYEE / ADMIN ID</label>
                <input
                  type="text"
                  placeholder="Enter your ID"
                  value={employeeId}
                  onChange={(e) => setEmployeeId(e.target.value)}
                  autoComplete="username"
                  maxLength={100}
                  required
                  className={inputClass}
                />
              </div>

              {/* PASSWORD FIELD WITH UPDATED EYE ICON */}
              <div>
                <label className={labelClass}>PASSWORD</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete={
                      mode === 'signup' ? 'new-password' : 'current-password'
                    }
                    minLength={mode === 'signup' ? 8 : undefined}
                    required
                    className={`${inputClass} pr-14`}
                  />
                  {/* EYE ICON BUTTON */}
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-[#800a1d] hover:text-[#800a1d]/70 focus:outline-none flex items-center justify-center p-1"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? (
                      // Open Eye (Show) - Reduced to 5 clean, spaced lashes
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M2 12 Q12 4 22 12 Q12 20 2 12 Z" />
                        <circle cx="12" cy="12" r="3.5" fill="currentColor" stroke="none" />
                        {/* 5 Upper Lashes */}
                        <path d="M5 8.8 L4 5.8" />
                        <path d="M8.5 7.3 L8 4.3" />
                        <path d="M12 6.8 L12 3.8" />
                        <path d="M15.5 7.3 L16 4.3" />
                        <path d="M19 8.8 L20 5.8" />
                      </svg>
                    ) : (
                      // Closed Eye (Hide) - Deep Curve with 7 Elegant Lashes (Kept as requested)
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M3 11 Q12 17 21 11" />
                        <path d="M4.5 12.5 Q3.5 13.5 3.5 14.5" />
                        <path d="M7 14 Q6 15.5 6 16.5" />
                        <path d="M9.5 15 Q8.5 17 8.5 18" />
                        <path d="M12 15.5 L12 17.5" />
                        <path d="M14.5 15 Q15.5 17 15.5 18" />
                        <path d="M17 14 Q18 15.5 18 16.5" />
                        <path d="M19.5 12.5 Q20.5 13.5 20.5 14.5" />
                      </svg>
                    )}
                  </button>
                </div>
                {mode === 'signup' && (
                  <p className="font-sans text-xs text-white/75 mt-2">
                    Use at least 8 characters.
                  </p>
                )}
              </div>

              {error && (
                <p role="alert" className="text-center font-sans text-sm text-[#ffd9d9]">
                  {error}
                </p>
              )}
              {successMsg && (
                <p role="alert" className="text-center font-sans text-sm text-[#cdeef2] font-bold">
                  {successMsg}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-[#cdeef2] text-[#800a1d] font-cinzel font-bold tracking-widest py-3 rounded-full hover:bg-white transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {loading
                  ? 'PLEASE WAIT…'
                  : mode === 'signup'
                    ? 'CREATE ACCOUNT'
                    : 'LOGIN'}
              </button>
            </form>

            <button
              type="button"
              onClick={switchMode}
              className="mt-5 text-center font-cinzel text-xs text-white/80 tracking-widest cursor-pointer hover:text-white transition-colors"
            >
              {mode === 'signup'
                ? 'ALREADY HAVE AN ACCOUNT? LOG IN'
                : 'NEW HERE? SIGN UP'}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}