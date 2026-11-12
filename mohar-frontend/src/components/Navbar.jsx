import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useRole } from '../context/RoleContext';

export default function Navbar({ isBackendOnline }) {
  const { currentRole, email, signOut } = useRole();
  const location = useLocation();
  const navigate = useNavigate();
  const cur = (path) => (location.pathname === path ? 'page' : undefined);

  const handleSignOut = () => { signOut(); navigate('/login'); };

  return (
    <header className="top glass">
      <Link to="/" className="logo">
        <span>MOHAR</span>
      </Link>
      {currentRole && (
        <nav className="tabs" aria-label="Main">
          <Link to="/" aria-current={cur('/')}>Workspace</Link>
          {currentRole === 'Creator' && <Link to="/submit" aria-current={cur('/submit')}>Submit</Link>}
          <Link to="/queue" aria-current={cur('/queue')}>Approvals</Link>
          <Link to="/dashboard" aria-current={cur('/dashboard')}>Dashboard</Link>
          {currentRole === 'Reviewer' && <Link to="/knowledge" aria-current={cur('/knowledge')}>Knowledge</Link>}
        </nav>
      )}
      {currentRole && (
        <div className="row" style={{ marginLeft: 'auto', gap: '10px' }}>
          <span className="chip id" title={email || ''}>{currentRole}{email ? ` · ${email.split('@')[0]}` : ''}</span>
          <span className={`chip ${isBackendOnline ? 'ready' : 'review'}`}>{isBackendOnline ? 'API online' : 'API waking'}</span>
          <button className="btn" onClick={handleSignOut}>Sign out</button>
        </div>
      )}
    </header>
  );
}
