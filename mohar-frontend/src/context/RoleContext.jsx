import React, { createContext, useContext, useEffect, useState } from 'react';
import { getSession, saveSession, clearSession } from '../services/api';

const RoleContext = createContext();

/* Real sign-in: the role comes from the server (verified token), not from a button. */
export function RoleProvider({ children }) {
  const [session, setSession] = useState(getSession());

  useEffect(() => {
    const onSignOut = () => setSession(null);
    window.addEventListener('mohar:signout', onSignOut);
    return () => window.removeEventListener('mohar:signout', onSignOut);
  }, []);

  const signIn = (payload) => setSession(saveSession(payload));
  const signOut = () => { clearSession(); setSession(null); };

  return (
    <RoleContext.Provider value={{
      session,
      currentRole: session ? session.role : null,
      email: session ? session.email : null,
      signIn,
      signOut,
    }}>
      {children}
    </RoleContext.Provider>
  );
}

export function useRole() {
  return useContext(RoleContext);
}
