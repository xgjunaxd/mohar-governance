import { useState, useEffect } from 'react';
import { supabase } from './lib/supabase';
import Login from './components/Login';
import Dashboard from './components/Dashboard'; // Your main app component

export default function App() {
  const [session, setSession] = useState(null);
  const [userRole, setUserRole] = useState(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      if (session) fetchRole(session.user.id);
    });

    supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      if (session) fetchRole(session.user.id);
    });
  }, []);

  const fetchRole = async (userId) => {
    const { data } = await supabase
      .from('user_roles')
      .select('role')
      .eq('user_id', userId)
      .single();
    setUserRole(data?.role || 'creator');
  };

  if (!session) {
    return <Login onLogin={(user) => {
      setSession({ user });
      setUserRole(user.role);
    }} />;
  }

  // Pass the verified role down to your components instead of the demo switcher
  return <Dashboard user={session.user} role={userRole} />;
}
