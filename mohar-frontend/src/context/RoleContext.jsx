// mohar-frontend/src/context/RoleContext.jsx
import React, { createContext, useState, useEffect, useContext } from 'react';
import { supabase } from '../lib/supabase';

export const RoleContext = createContext({
  role: 'submitter',
  setRole: () => {},
  user: null,
  setUser: () => {},
  logout: () => {},
});

export function RoleProvider({ children }) {
  const [role, setRoleState] = useState(() => {
    return localStorage.getItem('mohar_user_role') || 'submitter';
  });

  const [user, setUserState] = useState(() => {
    try {
      const saved = localStorage.getItem('mohar_demo_user');
      return saved ? JSON.parse(saved) : {
        email: 'submitter@mohar.demo',
        name: 'Demo Submitter',
        role: 'submitter',
      };
    } catch {
      return { email: 'submitter@mohar.demo', name: 'Demo Submitter', role: 'submitter' };
    }
  });

  const setRole = (newRole) => {
    const cleanRole = newRole || 'submitter';
    setRoleState(cleanRole);
    localStorage.setItem('mohar_user_role', cleanRole);

    const updatedUser = {
      ...(user || {}),
      role: cleanRole,
      name:
        cleanRole === 'admin'
          ? 'Demo Admin'
          : cleanRole === 'reviewer'
          ? 'Demo Reviewer'
          : 'Demo Submitter',
      email: `${cleanRole}@mohar.demo`,
    };
    setUserState(updatedUser);
    localStorage.setItem('mohar_demo_user', JSON.stringify(updatedUser));
  };

  const setUser = (userObj) => {
    setUserState(userObj);
    if (userObj) {
      localStorage.setItem('mohar_demo_user', JSON.stringify(userObj));
    }
  };

  const logout = async () => {
    try {
      await supabase?.auth?.signOut();
    } catch {
      // Ignore network errors on sign out
    }
    localStorage.removeItem('mohar_user_role');
    localStorage.removeItem('mohar_demo_user');
    setUserState(null);
    setRoleState('submitter');
  };

  useEffect(() => {
    // Check if an active Supabase session exists on page refresh
    let mounted = true;
    if (supabase?.auth?.getSession) {
      supabase.auth.getSession().then(({ data }) => {
        if (mounted && data?.session?.user) {
          const sbUser = data.session.user;
          const sbRole = sbUser.user_metadata?.role || localStorage.getItem('mohar_user_role') || 'submitter';
          setRoleState(sbRole);
          setUserState({
            id: sbUser.id,
            email: sbUser.email,
            name: sbUser.user_metadata?.full_name || sbUser.email.split('@')[0],
            role: sbRole,
          });
        }
      }).catch(() => {});
    }
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <RoleContext.Provider value={{ role, setRole, user, setUser, logout }}>
      {children}
    </RoleContext.Provider>
  );
}

export const useRole = () => useContext(RoleContext);
export default RoleContext;
