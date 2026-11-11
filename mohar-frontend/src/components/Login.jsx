import { useState } from 'react';
import { supabase } from '../lib/supabase';

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      setError(error.message);
    } else {
      // Fetch the user's role from the database
      const { data: roleData } = await supabase
        .from('user_roles')
        .select('role')
        .eq('user_id', data.user.id)
        .single();
        
      onLogin({ ...data.user, role: roleData?.role || 'creator' });
    }
    setLoading(false);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-black text-white">
      <form onSubmit={handleLogin} className="p-8 border border-gray-800 rounded-lg shadow-xl w-96 bg-gray-900">
        <h2 className="text-2xl font-bold mb-6 text-center text-red-500">MOHAR SECURE LOGIN</h2>
        {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
        <input
          type="email"
          placeholder="Work Email"
          className="w-full p-3 mb-4 bg-gray-800 border border-gray-700 rounded text-white focus:outline-none focus:border-red-500"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password"
          className="w-full p-3 mb-6 bg-gray-800 border border-gray-700 rounded text-white focus:outline-none focus:border-red-500"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button 
          type="submit" 
          disabled={loading}
          className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3 rounded transition-colors disabled:opacity-50"
        >
          {loading ? 'Authenticating...' : 'Sign In'}
        </button>
      </form>
    </div>
  );
}
