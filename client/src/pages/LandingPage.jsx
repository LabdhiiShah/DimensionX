
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import CinzelFont from '../components/CinzelFont.jsx';
import { authApi, saveSession } from '../lib/api.js';

export default function LandingPage() {
  const [showLogin, setShowLogin] = useState(true);
  const [mode, setMode] = useState('login');

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [employeeId, setEmployeeId] = useState('');
  const [password, setPassword] = useState('');

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data =
        mode === 'signup'
          ? await authApi.signup(
              fullName.trim(),
              email.trim(),
              employeeId.trim(),
              password
            )
          : await authApi.login(employeeId.trim(), password);

      saveSession(data);

      // Admin routing can be added when the admin dashboard is ready.
      navigate(data.isAdmin ? '/admin' : '/projects');
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setMode((current) =>
      current === 'login' ? 'signup' : 'login'
    );
    setError('');
    setPassword('');
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

              <div>
                <label className={labelClass}>PASSWORD</label>
                <input
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={
                    mode === 'signup' ? 'new-password' : 'current-password'
                  }
                  minLength={mode === 'signup' ? 8 : undefined}
                  required
                  className={inputClass}
                />
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
              className="mt-5 text-center font-cinzel text-xs text-white/80  tracking-widest cursor-pointer"
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
