import React, { useState, useEffect } from 'react';
import Skeleton from '../components/Skeleton';
import { getWorkspace } from '../services/api';

export default function Workspace() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadWorkspace() {
    setLoading(true);
    setError('');

    try {
      const res = await getWorkspace();
      setData(res.data);
    } catch {
      setError('Could not load the workspace. Check the server and retry.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadWorkspace();
  }, []);

  if (loading) return <Skeleton rows={3} label="Loading workspace" note="Waking up the server. On free hosting this can take up to a minute." />;

  if (error) {
    return (
      <main>
        <div className="glass pad">
          <p role="alert">{error}</p>
          <button className="btn primary" onClick={loadWorkspace}>
            Retry
          </button>
        </div>
      </main>
    );
  }

  return (
    <main>
      <div className="glass hero sheen">
        <h1>Brand Governance Workspace</h1>
        <p>Official guidelines, compliance rules, and verified facts for AstraPay.</p>
      </div>

      <h2 className="sec">Brand Rules &amp; Guidelines</h2>
      <div className="grid">
        {data?.rules?.map((rule) => (
          <article key={rule.id} className="glass pad hoverlift">
            <div className="row" style={{ marginBottom: '10px' }}>
              <span className="chip id">{rule.id}</span>
              <span
                className={`chip ${
                  rule.severity === 'high'
                    ? 'blocked'
                    : rule.severity === 'medium'
                      ? 'review'
                      : 'ready'
                }`}
              >
                {rule.severity}
              </span>
            </div>
            <h3>{rule.category.replace('_', ' ')}</h3>
            <p style={{ margin: '8px 0 12px' }}>{rule.text}</p>
          </article>
        ))}
      </div>

      <h2 className="sec" style={{ marginTop: '40px' }}>
        Approved Facts Ledger
      </h2>
      <div className="grid">
        {data?.facts?.map((fact) => (
          <article key={fact.id} className="glass pad hoverlift">
            <div className="row" style={{ marginBottom: '10px' }}>
              <span className="chip id">{fact.id}</span>
              {fact.expires_on && (
                <span className={`chip ${String(fact.status).toLowerCase() === 'expired' ? 'blocked' : 'review'}`}>
                  {String(fact.status).toLowerCase() === 'expired' ? 'Expired' : 'Expires'}: {fact.expires_on}
                </span>
              )}
              {fact.version > 1 && <span className="chip info">v{fact.version}</span>}
            </div>
            <p style={{ margin: '8px 0 12px' }}>{fact.approved_text}</p>
            <div className="label">Source: {fact.source}</div>
          </article>
        ))}
      </div>

      {/* --- New Contact Form Section --- */}
      <h2 className="sec" style={{ marginTop: '40px' }}>
        Contact Governance Team
      </h2>
      <div className="glass pad" style={{ maxWidth: '500px', marginBottom: '40px' }}>
        <form 
          onSubmit={async (e) => {
            e.preventDefault();
            const formData = {
              name: e.target.name.value,
              email: e.target.email.value,
              message: e.target.message.value
            };
            
            try {
              const response = await fetch(`${import.meta.env.VITE_API_URL || 'https://mohar-api.onrender.com'}/contact`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
              });
              
              if (response.ok) {
                alert("Message Sent Successfully!");
                e.target.reset(); // Clears the form after success
              } else {
                alert("Failed to send. Is the backend awake?");
              }
            } catch (err) {
              alert("Network error. Could not reach the server.");
            }
          }}
          style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}
        >
          <input 
            type="text" 
            name="name" 
            placeholder="Your Name" 
            required 
            style={{ padding: '12px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(255,255,255,0.05)', color: 'inherit', fontFamily: 'inherit' }} 
          />
          <input 
            type="email" 
            name="email" 
            placeholder="Your Email" 
            required 
            style={{ padding: '12px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(255,255,255,0.05)', color: 'inherit', fontFamily: 'inherit' }} 
          />
          <textarea 
            name="message" 
            placeholder="Your Message..." 
            required 
            rows="4" 
            style={{ padding: '12px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(255,255,255,0.05)', color: 'inherit', fontFamily: 'inherit', resize: 'vertical' }}
          ></textarea>
          <button 
            type="submit" 
            className="btn primary"
            style={{ padding: '12px', width: '100%', fontSize: '1rem' }}
          >
            Send Message
          </button>
        </form>
      </div>
    </main>
  );
}
