import { toast } from '../utils/toast';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TIMEOUT_MS = 90000; // free hosting can take up to ~60s to wake up
const SESSION_KEY = 'mohar.session';

/* ---------- session (kept in this browser tab only) ---------- */
export function getSession() {
  try {
    const s = JSON.parse(sessionStorage.getItem(SESSION_KEY));
    if (s && s.token && s.expires_at > Date.now()) return s;
  } catch { /* no saved session */ }
  return null;
}
export function saveSession(payload) {
  const s = {
    token: payload.access_token,
    email: payload.email,
    role: payload.role,
    expires_at: Date.now() + (payload.expires_in || 3600) * 1000 - 30000,
  };
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(s));
  return s;
}
export function clearSession() {
  sessionStorage.removeItem(SESSION_KEY);
}

/* ---------- one request helper: adds the token, turns errors into readable messages ---------- */
async function request(path, { method = 'GET', body, form, fallback = 'Request failed' } = {}) {
  const headers = { Accept: 'application/json' };
  const session = getSession();
  if (session) headers.Authorization = `Bearer ${session.token}`;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { method, headers, body: payload, signal: controller.signal });
  } catch (err) {
    const msg = err.name === 'AbortError'
      ? 'The server is taking too long to answer. It may be waking up, please try again in a moment.'
      : 'Cannot reach the server. Check your internet connection and try again.';
    toast(msg, 'error');
    throw new Error(msg);
  } finally {
    clearTimeout(timer);
  }
  if (!response.ok) {
    let reason = `${fallback} (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data.detail === 'string') reason = data.detail;
      else if (Array.isArray(data.detail)) reason = 'Please check the fields you filled in.';
    } catch { /* no JSON body */ }
    if (response.status === 401 && session) {
      clearSession();
      window.dispatchEvent(new Event('mohar:signout'));
      reason = 'Your session expired. Please sign in again.';
    }
    if (!path.startsWith('/api/auth/')) toast(reason, 'error');
    throw new Error(reason);
  }
  const data = await response.json();
  const done = SUCCESS_MESSAGES.find(([m, re]) => m === method && re.test(path));
  if (done) toast(done[2]);
  return data;
}

const SUCCESS_MESSAGES = [
  ['POST', /^\/api\/submissions$/, 'Review complete'],
  ['POST', /^\/api\/visual-review$/, 'Image review complete'],
  ['POST', /^\/api\/submissions\/[^/]+\/resubmit$/, 'New version analysed'],
  ['POST', /^\/api\/submissions\/[^/]+\/approval$/, 'Decision recorded'],
  ['POST', /^\/api\/findings\/[^/]+\/decision$/, 'Decision saved'],
  ['POST', /^\/api\/facts$/, 'Fact added'],
  ['PUT', /^\/api\/(facts|rules)\//, 'Saved'],
  ['POST', /^\/api\/auth\//, 'Signed in'],
];

/* ---------- sign-in ---------- */
export const login = (email, password) => request('/api/auth/login', { method: 'POST', body: { email, password }, fallback: 'Sign-in failed' });
export const demoLogin = (role) => request('/api/auth/demo', { method: 'POST', body: { role }, fallback: 'Demo sign-in failed' });

/* ---------- workspace + health ---------- */
export async function getWorkspace() {
  const data = await request('/api/workspace');
  return { data, isMock: false };
}

export async function checkBackendHealth() {
  try {
    const response = await fetch(`${BASE_URL}/health`, { signal: AbortSignal.timeout(3000) });
    return response.ok;
  } catch {
    return false;
  }
}

/* ---------- creator flow ---------- */
export const submitPost = (payload) => request('/api/submissions', { method: 'POST', body: payload, fallback: 'Submission failed' });
export const getSubmissionDetail = (id) => request(`/api/submissions/${id}`, { fallback: 'Failed to fetch submission detail' });
export const recordDecision = (findingId, payload) => request(`/api/findings/${findingId}/decision`, { method: 'POST', body: payload, fallback: 'Failed to record decision' });
export const resubmitPost = (subId, newText) => request(`/api/submissions/${subId}/resubmit`, { method: 'POST', body: { text: newText }, fallback: 'Resubmission failed' });

export function submitVisual(file, altText, title) {
  const form = new FormData();
  form.append('file', file);
  form.append('alt_text', altText || '');
  form.append('title', title || 'Image asset');
  return request('/api/visual-review', { method: 'POST', form, fallback: 'Image review failed' });
}

/* ---------- manager + dashboard ---------- */
export const getSubmissions = () => request('/api/submissions', { fallback: 'Failed to fetch queue' });
export const submitApproval = (subId, payload) => request(`/api/submissions/${subId}/approval`, { method: 'POST', body: payload, fallback: 'Approval failed' });
export const getDashboard = () => request('/api/dashboard', { fallback: 'Failed to fetch dashboard metrics' });
export const getAlerts = () => request('/api/alerts/expiring', { fallback: 'Failed to fetch expiry alerts' });

/* ---------- reviewer workspace ---------- */
export const getConflicts = () => request('/api/facts/conflicts', { fallback: 'Failed to check conflicts' });
export const getFactVersions = (id) => request(`/api/facts/${id}/versions`, { fallback: 'Failed to load history' });
export const updateFact = (id, payload) => request(`/api/facts/${id}`, { method: 'PUT', body: payload, fallback: 'Could not save the fact' });
export const createFact = (payload) => request('/api/facts', { method: 'POST', body: payload, fallback: 'Could not add the fact' });
export const updateRule = (id, payload) => request(`/api/rules/${id}`, { method: 'PUT', body: payload, fallback: 'Could not save the rule' });
