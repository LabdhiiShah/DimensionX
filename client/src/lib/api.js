// One place for every call to the Express server. Attaches the login token automatically.
const API_ROOT = import.meta.env.VITE_API_URL || 'http://localhost:4000/api';
const TOKEN_KEY = 'dimensionsx_token';
const USER_KEY = 'dimensionsx_user';

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const getUser = () => {
  try { return JSON.parse(localStorage.getItem(USER_KEY)) || null; } catch { return null; }
};
export function saveSession({ token, username, isAdmin }) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify({ username, isAdmin }));
}
export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

async function request(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${API_ROOT}${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined });
  } catch {
    throw new Error('Could not reach the server. Is it running on port 4000?');
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || 'Something went wrong. Please try again.');
    err.status = res.status;
    // Expired / invalid token on a protected call: drop the session so the app sends the user to login.
    if (res.status === 401 && !path.startsWith('/auth/')) clearSession();
    throw err;
  }
  return data;
}

export const authApi = {
  login: (employeeId, password) => request('/auth/login', { method: 'POST', body: { employeeId, password } }),
  signup: (employeeId, password) => request('/auth/signup', { method: 'POST', body: { employeeId, password } }),
};

export const projectsApi = {
  list: () => request('/projects'),
  create: (project) => request('/projects', { method: 'POST', body: project }),
};
