import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, demoLogin } from '../services/api';
import { useRole } from '../context/RoleContext';

const HOME = { Creator: '/submit', Manager: '/queue', Reviewer: '/knowledge' };

export default function Login() {
  const { signIn } = useRole();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const finish = (payload) => {
    signIn(payload);
    navigate(HOME[payload.role] || '/');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try { finish(await login(email.trim(), password)); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  const handleDemo = async (role) => {
    setBusy(true); setError('');
    try { finish(await demoLogin(role)); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  return (
    <main>
      <div className="glass hero sheen">
        <h1>Sign in to Mohar</h1>
        <p>Your role (Creator, Manager or Reviewer) is set on the server, so each person only sees what their role allows.</p>
      </div>

      {error && <div className="glass pad" role="alert" style={{ marginBottom: '18px', color: 'var(--blocked)' }}>{error}</div>}

      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))' }}>
        <form onSubmit={handleLogin} className="glass pad hoverlift">
          <h3 style={{ marginTop: 0 }}>Team sign-in</h3>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" autoComplete="username" required maxLength={200} value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input id="password" type="password" autoComplete="current-password" required maxLength={200} value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button type="submit" className="btn primary" disabled={busy} style={{ width: '100%' }}>
            {busy ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="glass pad hoverlift">
          <h3 style={{ marginTop: 0 }}>Judges: try it in one click</h3>
          <p style={{ marginBottom: '16px' }}>These are real demo accounts with real roles. No sign-up needed.</p>
          <div style={{ display: 'grid', gap: '10px' }}>
            <button className="btn" disabled={busy} onClick={() => handleDemo('Creator')}>Sign in as Creator</button>
            <button className="btn" disabled={busy} onClick={() => handleDemo('Manager')}>Sign in as Manager</button>
            <button className="btn" disabled={busy} onClick={() => handleDemo('Reviewer')}>Sign in as Reviewer</button>
          </div>
          {busy && <p style={{ marginTop: '14px', fontSize: '13px' }}>Waking up the server, this can take up to a minute...</p>}
        </div>
      </div>
    </main>
  );
}
