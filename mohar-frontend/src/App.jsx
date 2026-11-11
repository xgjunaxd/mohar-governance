import { useState, useEffect } from 'react';
import { supabase } from './lib/supabase';
import Login from './components/Login';
import FactEditor from './components/FactEditor';
import Navbar from './components/Navbar'; // Assuming your Navbar is here
// Import your existing workspace components below
// import CreatorWorkspace from './components/CreatorWorkspace';
// import ApprovalQueue from './components/ApprovalQueue';

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

  // 1. If not logged in, show the Login screen
  if (!session) {
    return <Login onLogin={(user) => {
      setSession({ user });
      setUserRole(user.role);
    }} />;
  }

  // 2. If logged in, show the Navbar and the correct workspace based on role
  return (
    <div className="min-h-screen bg-black text-white font-sans">
      <Navbar user={session.user} role={userRole} />
      
      <main className="pt-4">
        {userRole === 'reviewer' && (
          <FactEditor user={session.user} token={session.access_token} />
        )}
        
        {/* Replace these divs with your actual components */}
        {userRole === 'manager' && (
          <div className="p-8">Manager Approval Queue Component Goes Here</div>
        )}
        
        {userRole === 'creator' && (
          <div className="p-8">Creator Workspace Component Goes Here</div>
        )}
      </main>
    </div>
  );
}
