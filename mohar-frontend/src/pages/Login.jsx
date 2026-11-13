import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, demoLogin } from '../services/api';
import { useRole } from '../context/RoleContext';
import TubesLayer from '../components/TubesLayer';

const HOME = { Creator: '/submit', Manager: '/queue', Reviewer: '/knowledge' };
const REPO = 'https://github.com/xgjunaxd/mohar-governance';

/* ---------- small inline icons (no external files) ---------- */
const Diamond = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
    <defs>
      <linearGradient id="mh-diamond" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#ffb347" /><stop offset="1" stopColor="#ff2f3a" />
      </linearGradient>
    </defs>
    <path d="M12 2 22 12 12 22 2 12z" fill="url(#mh-diamond)" />
  </svg>
);
const Svg = ({ children, size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {children}
  </svg>
);
const IconPen = () => <Svg><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></Svg>;
const IconCheck = () => <Svg><path d="M20 6 9 17l-5-5" /></Svg>;
const IconBook = () => <Svg><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5Z" /><path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5" /></Svg>;
const IconShield = () => <Svg><path d="M12 3 4 6v6c0 5 3.4 8 8 9 4.6-1 8-4 8-9V6Z" /></Svg>;
const IconSearch = () => <Svg><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></Svg>;
const IconFlag = () => <Svg><path d="M5 21V4" /><path d="M5 4h12l-2 4 2 4H5" /></Svg>;
const IconClock = () => <Svg><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></Svg>;

const EXAMPLE_ROWS = [
  { icon: <IconShield />, label: 'Guaranteed-returns claim', arg: 'CL-001', chip: 'Blocked', tone: 'blocked' },
  { icon: <IconFlag />, label: 'Market-risk disclaimer missing', arg: 'DS-001', chip: 'Blocked', tone: 'blocked' },
  { icon: <IconBook />, label: 'Rate differs from approved fact', arg: 'F-008', chip: 'Needs review', tone: 'review' },
  { icon: <IconClock />, label: 'Unproven "fastest" claim', arg: 'CL-002', chip: 'Needs review', tone: 'review' },
];

const PILLARS = [
  ['01', 'No source, no flag', 'Every finding carries a verified rule or fact ID and the exact excerpt. Anything unverified is marked for a human.'],
  ['02', 'Hybrid engine', 'Plain code checks the objective rules. One AI call looks at tone and implied claims.'],
  ['03', 'Fact ledger', 'Approved facts have owners, versions and expiry dates, so old fees and offers stop slipping through.'],
  ['04', 'Decision trail', 'Accept, edit or reject each fix. Managers approve. Every step is in the audit log.'],
];

export default function Login() {
  const { signIn } = useRole();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  /* tells the global CSS to show the aurora at full strength on this page */
  useEffect(() => {
    document.documentElement.classList.add('is-hero');
    return () => document.documentElement.classList.remove('is-hero');
  }, []);

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
    <div className="mh-root">
      <TubesLayer />

      <div className="mh-layer">
        <nav className="mh-nav" aria-label="Main">
          <a className="mh-brand" href="#top"><Diamond />Mohar</a>
          <div className="mh-links">
            <a href="#how">How it works</a>
            <a href="#signin">Sign in</a>
            <a href={REPO} target="_blank" rel="noopener noreferrer">Source</a>
          </div>
          <div className="mh-navr">
            <a className="mh-login" href="#signin">Log in</a>
            <a className="mh-pill-btn" href="#top">Try the demo</a>
          </div>
        </nav>

        <header className="mh-hero" id="top">
          <div className="mh-eyebrow">Round 3 · now with image checks and real sign-in</div>
          <h1 className="mh-h1">Every claim has<br /><span className="mh-accent">evidence</span>.</h1>
          <p className="mh-sub">
            Mohar checks posts and images against your approved brand rules and facts before anything is published. No source, no flag.
          </p>

          {error && <div className="mh-error" role="alert">{error}</div>}

          <div className="mh-cta" role="group" aria-label="Try the live demo">
            <button type="button" className="mh-key" disabled={busy} onClick={() => handleDemo('Creator')}><IconPen />Sign in as Creator</button>
            <button type="button" className="mh-key" disabled={busy} onClick={() => handleDemo('Manager')}><IconCheck />Sign in as Manager</button>
            <button type="button" className="mh-key" disabled={busy} onClick={() => handleDemo('Reviewer')}><IconBook />Sign in as Reviewer</button>
          </div>
          <div className="mh-caption mh-mono" aria-live="polite">
            {busy ? 'Waking up the server, this can take up to a minute...' : 'No install, no sign-up · live demo accounts with real roles'}
          </div>
        </header>

        <div className="mh-cmd" role="img" aria-label="Example of a Mohar review: four flagged issues, each with a rule or fact ID">
          <div className="mh-cmd-top">
            <IconSearch />
            <div className="mh-cmd-q">check: guaranteed 10% returns on savings<span className="mh-caret" /></div>
            <span className="mh-mode mh-mono">Review</span>
          </div>
          <div className="mh-rows">
            {EXAMPLE_ROWS.map((r, i) => (
              <div key={r.arg} className={`mh-row${i === 0 ? ' active' : ''}`}>
                {r.icon}
                <span>{r.label}<span className="arg mh-mono">{r.arg}</span></span>
                <span className={`mh-chip mh-mono ${r.tone}`}>{r.chip}</span>
              </div>
            ))}
          </div>
          <div className="mh-foot mh-mono"><span>example review · every flag cites a rule or fact ID</span><span>Mohar</span></div>
        </div>

        <section className="mh-section" id="signin" aria-labelledby="signin-title">
          <h2 id="signin-title" className="mh-h2">Team sign-in</h2>
          <form onSubmit={handleLogin} className="mh-card">
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
            <p className="mh-note">Your role (Creator, Manager or Reviewer) is set on the server, so each person only sees what their role allows.</p>
          </form>
        </section>

        <section className="mh-section" id="how" aria-labelledby="how-title">
          <h2 id="how-title" className="mh-h2">How Mohar works</h2>
          <div className="mh-pillars">
            {PILLARS.map(([n, t, d]) => (
              <article key={n} className="mh-card">
                <div className="mh-pillar-n mh-mono">{n}</div>
                <h3>{t}</h3>
                <p>{d}</p>
              </article>
            ))}
          </div>
        </section>

        <div className="mh-ghost-wrap">
          <a className="mh-ghost" href={REPO} target="_blank" rel="noopener noreferrer">View source on GitHub →</a>
        </div>

        <aside className="mh-badge" aria-label="CodeNexus India 2026, Round 3 finalist">
          <div className="mh-badge-mark"><Diamond /></div>
          <div><b>CodeNexus India 2026</b><span>Round 3 finalist · Top 50</span></div>
        </aside>
      </div>
    </div>
  );
}
