import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useRole } from '../context/RoleContext';

export default function Navbar({ isBackendOnline }) {
  const { currentRole, setRole } = useRole();
  const location = useLocation();

  return (
    <header className="top glass">
      <Link to="/" className="logo">
        <span>MOHAR</span>
      </Link>
      <nav className="tabs" aria-label="Main">
        <Link to="/" aria-current={location.pathname === '/' ? "page" : undefined}>Workspace</Link>
        <Link to="/submit" aria-current={location.pathname === '/submit' ? "page" : undefined}>Submit</Link>
        <Link to="/queue" aria-current={location.pathname === '/queue' ? "page" : undefined}>Approvals</Link>
        <Link to="/dashboard" aria-current={location.pathname === '/dashboard' ? "page" : undefined}>Dashboard</Link>
      </nav>
      <div className="seg" role="group" aria-label="Role switcher">
        {['Creator', 'Manager', 'Reviewer'].map(r => (
          <button 
            key={r} 
            onClick={() => setRole(r)}
            aria-pressed={currentRole === r}
          >
            {r}
          </button>
        ))}
      </div>
    </header>
  );
}
