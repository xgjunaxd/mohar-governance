import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useRole } from '../context/RoleContext';

export default function Navbar({ isBackendOnline }) {
  const { currentRole, email, signOut } = useRole();
  const location = useLocation();
  const navigate = useNavigate();
  const cur = (path) => (location.pathname === path ? 'page' : undefined);

  // The sign-in page has its own floating navigation.
  if (!currentRole) return null;

  const handleSignOut = () => { signOut(); navigate('/'); };
  const who = email ? email.split('@')[0] : '';
  const showWho = who && who.toLowerCase() !== currentRole.toLowerCase();

  return (
    <header className="top glass">
      <Link to="/" className="logo">
        <span>Mohar</span>
      </Link>
      <nav className="tabs" aria-label="Main">
        <Link to="/" aria-current={cur('/')}>Workspace</Link>
        {currentRole === 'Creator' && <Link to="/submit" aria-current={cur('/submit')}>Submit</Link>}
        <Link to="/queue" aria-current={cur('/queue')}>Approvals</Link>
        <Link to="/dashboard" aria-current={cur('/dashboard')}>Dashboard</Link>
        {currentRole === 'Reviewer' && <Link to="/knowledge" aria-current={cur('/knowledge')}>Knowledge</Link>}
      </nav>
      <div className="row nav-right">
        <span className="chip id" title={email || ''}>{currentRole}{showWho ? ` · ${who}` : ''}</span>
        <span className={`chip ${isBackendOnline ? 'ready' : 'review'}`}>{isBackendOnline ? 'API online' : 'API waking'}</span>
        <button className="btn" onClick={handleSignOut}>Sign out</button>
      </div>
    </header>
  );
}
