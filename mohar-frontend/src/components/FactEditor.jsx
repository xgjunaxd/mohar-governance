import { useState, useEffect } from 'react';

export default function FactEditor({ user, token }) {
  const [facts, setFacts] = useState([]);
  const [expiringAlerts, setExpiringAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Form State
  const [category, setCategory] = useState('');
  const [factText, setFactText] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  const [conflictWarning, setConflictWarning] = useState(null);

  const API_URL = import.meta.env.VITE_API_URL || 'https://mohar-api.onrender.com';

  useEffect(() => {
    fetchFacts();
  }, []);

  const fetchFacts = async () => {
    try {
      // In a real app, this calls your backend GET /facts route
      // Fallback to Supabase if backend isn't ready
      const response = await fetch(`${API_URL}/facts`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setFacts(data.facts || []);
        
        // Filter facts expiring in the next 30 days
        const thirtyDaysFromNow = new Date();
        thirtyDaysFromNow.setDate(thirtyDaysFromNow.getDate() + 30);
        
        const expiring = (data.facts || []).filter(fact => {
          if (!fact.expiry_date) return false;
          return new Date(fact.expiry_date) <= thirtyDaysFromNow;
        });
        setExpiringAlerts(expiring);
      }
    } catch (err) {
      console.error("Failed to fetch facts:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddFact = async (e) => {
    e.preventDefault();
    setError(null);
    setConflictWarning(null);

    const payload = {
      category,
      fact_text: factText,
      expiry_date: expiryDate,
      owner: user.email
    };

    try {
      const response = await fetch(`${API_URL}/facts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      const result = await response.json();

      if (result.warning) {
        setConflictWarning(result.warning); // Shows conflict with existing facts
      } else {
        // Reset form on clean success
        setCategory('');
        setFactText('');
        setExpiryDate('');
        fetchFacts(); 
      }
    } catch (err) {
      setError("Failed to save fact. Check your backend connection.");
    }
  };

  if (loading) return <div className="text-gray-400 p-8">Loading Fact Ledger...</div>;

  return (
    <div className="p-8 text-white max-w-5xl mx-auto space-y-8">
      <div className="flex justify-between items-end border-b border-gray-800 pb-4">
        <div>
          <h1 className="text-3xl font-bold text-red-500 tracking-wider">FACT LEDGER</h1>
          <p className="text-gray-400 text-sm mt-1">Reviewer Workspace: Manage verifiable brand facts and lifecycle.</p>
        </div>
      </div>

      {expiringAlerts.length > 0 && (
        <div className="bg-red-900/30 border border-red-500/50 p-4 rounded-lg">
          <h3 className="text-red-400 font-bold mb-2">⚠️ Expiry Alerts</h3>
          <ul className="list-disc pl-5 text-sm text-red-200 space-y-1">
            {expiringAlerts.map((f, i) => (
              <li key={i}>
                <strong>{f.category}</strong> expires on {f.expiry_date} - <em>"{f.fact_text}"</em>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Form Section */}
        <div className="md:col-span-1 bg-gray-900 border border-gray-800 p-6 rounded-lg h-fit">
          <h2 className="text-xl font-semibold mb-4 border-b border-gray-800 pb-2">Add New Fact</h2>
          <form onSubmit={handleAddFact} className="space-y-4">
            {error && <div className="text-red-400 text-xs">{error}</div>}
            {conflictWarning && <div className="text-yellow-400 text-xs bg-yellow-900/20 p-2 border border-yellow-700">{conflictWarning}</div>}
            
            <div>
              <label className="block text-xs text-gray-500 uppercase tracking-wider mb-1">Category</label>
              <input 
                type="text" 
                required 
                className="w-full bg-black border border-gray-700 rounded p-2 text-sm focus:border-red-500 focus:outline-none"
                value={category}
                onChange={e => setCategory(e.target.value)}
                placeholder="e.g., Pricing, Limits"
              />
            </div>
            
            <div>
              <label className="block text-xs text-gray-500 uppercase tracking-wider mb-1">Approved Fact Text</label>
              <textarea 
                required 
                className="w-full bg-black border border-gray-700 rounded p-2 text-sm focus:border-red-500 focus:outline-none h-24"
                value={factText}
                onChange={e => setFactText(e.target.value)}
                placeholder="e.g., The daily UPI limit is Rs. 1,00,000."
              />
            </div>

            <div>
              <label className="block text-xs text-gray-500 uppercase tracking-wider mb-1">Expiry Date</label>
              <input 
                type="date" 
                required 
                className="w-full bg-black border border-gray-700 rounded p-2 text-sm text-gray-300 focus:border-red-500 focus:outline-none"
                value={expiryDate}
                onChange={e => setExpiryDate(e.target.value)}
              />
            </div>

            <button type="submit" className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-2 rounded text-sm transition-colors">
              Seal & Save Fact
            </button>
          </form>
        </div>

        {/* List Section */}
        <div className="md:col-span-2 space-y-4">
          <h2 className="text-xl font-semibold mb-4">Active Knowledge Base</h2>
          {facts.length === 0 ? (
            <p className="text-gray-500 text-sm">No facts stored yet.</p>
          ) : (
            facts.map((fact, idx) => (
              <div key={idx} className="bg-black border border-gray-800 p-4 rounded-lg flex justify-between items-start hover:border-gray-600 transition-colors">
                <div>
                  <span className="text-xs font-bold text-red-500 bg-red-950 px-2 py-1 rounded uppercase tracking-wider mr-2">
                    {fact.category}
                  </span>
                  <span className="text-gray-500 text-xs">Owner: {fact.owner}</span>
                  <p className="mt-2 text-sm text-gray-300">{fact.fact_text}</p>
                </div>
                <div className="text-right flex flex-col items-end">
                  <span className="text-xs text-gray-500 uppercase tracking-wider mb-1">Valid Until</span>
                  <span className="text-sm font-mono text-gray-300 bg-gray-900 px-2 py-1 rounded border border-gray-800">
                    {fact.expiry_date}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
