import React, { useState, useEffect } from 'react';
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

  if (loading) {
    return (
      <main>
        <div
          className="flex h-screen items-center justify-center text-gray-700"
          style={{ minHeight: '60vh' }}
        >
          <p
            className="text-lg font-medium animate-pulse"
            style={{ textAlign: 'center' }}
          >
            Waking up the server (this can take up to 60 seconds)...
          </p>
        </div>
      </main>
    );
  }

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
                <span className="chip review">Expires: {fact.expires_on}</span>
              )}
            </div>
            <p style={{ margin: '8px 0 12px' }}>{fact.approved_text}</p>
            <div className="label">Source: {fact.source}</div>
          </article>
        ))}
      </div>
    </main>
  );
}
