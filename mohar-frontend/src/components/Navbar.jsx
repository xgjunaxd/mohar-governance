// mohar-frontend/src/components/Navbar.jsx
import React, { useContext } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { RoleContext } from '../context/RoleContext';

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/' },
  { label: 'Submit Check', path: '/submit' },
  { label: 'Review Queue', path: '/queue' },
  { label: 'Findings', path: '/findings' },
  { label: 'Knowledge Base', path: '/knowledge' },
];

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { role, setRole, user, logout } = useContext(RoleContext);

  const handleLogout = async () => {
    if (logout) await logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-40 bg-slate-950/90 backdrop-blur-md border-b border-slate-800 text-slate-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        
        {/* Brand Logo */}
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-md shadow-indigo-600/30">
              M
            </div>
            <div>
              <span className="font-bold text-base tracking-tight text-white group-hover:text-indigo-300 transition-colors">
                MOHAR
              </span>
              <span className="hidden sm:inline-block ml-1.5 text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 uppercase">
                Governance
              </span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map((item) => {
              const isActive =
                item.path === '/'
                  ? location.pathname === '/'
                  : location.pathname.startsWith(item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                      : 'text-slate-400 hover:text-white hover:bg-slate-900'
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right Controls: Live Judge Role Switcher & Auth */}
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-1">
            <span className="text-[10px] uppercase tracking-wider text-slate-400 px-2 hidden sm:inline">
              Active Role:
            </span>
            {['submitter', 'reviewer', 'admin'].map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRole && setRole(r)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium capitalize transition-all ${
                  role === r
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {r}
              </button>
            ))}
          </div>

          {user ? (
            <button
              type="button"
              onClick={handleLogout}
              className="text-xs px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors"
            >
              Switch Account
            </button>
          ) : (
            <Link
              to="/login"
              className="text-xs px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition-colors"
            >
              Sign In
            </Link>
          )}
        </div>
      </div>

      {/* Mobile Navigation Bar */}
      <div className="md:hidden flex items-center gap-1 overflow-x-auto px-4 py-2 border-t border-slate-900 bg-slate-950">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.path === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.path);
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`px-3 py-1 rounded-md text-xs font-medium shrink-0 ${
                isActive
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400'
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </div>
    </header>
  );
}
