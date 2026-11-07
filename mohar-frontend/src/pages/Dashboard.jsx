import React, { useState, useEffect } from 'react';
import { getDashboard } from '../services/api';

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadDashboard() {
    setLoading(true);
    setError('');

    try {
      const response = await getDashboard();
      const data = response?.data ?? response;

      if (!data || typeof data !== 'object') {
        throw new Error('The dashboard returned an unexpected response.');
      }

      const categoryCounts = data.counts_by_category ?? {};

      const rawRules =
        data.most_violated_rules ??
        data.rule_violations ??
        [];

      const ruleEntries = Array.isArray(rawRules)
        ? rawRules.map((item) => [
            item.rule ?? item.id ?? 'Unknown rule',
            Number(item.count ?? 0),
          ])
        : Object.entries(rawRules).map(([rule, count]) => [
            rule,
            Number(count ?? 0),
          ]);

      const totalFindings =
        data.total_findings ??
        Object.values(categoryCounts).reduce(
          (total, count) => total + Number(count ?? 0),
          0
        );

      setMetrics({
        pendingReviews: Number(data.pending_reviews ?? 0),
        totalFindings: Number(totalFindings),
        categoryCounts,
        ruleEntries,
      });
    } catch (err) {
      console.error('Could not load dashboard:', err);
      setError('Could not load analytics. Check the server and retry.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  if (loading) {
    return (
      <main>
        <div className="glass hero sheen hoverlift">
          <h2>Loading Analytics...</h2>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main>
        <div className="glass pad">
          <p role="alert">{error}</p>
          <button className="btn primary" onClick={loadDashboard}>
            Retry
          </button>
        </div>
      </main>
    );
  }

  return (
    <main>
      <div className="glass hero sheen hoverlift">
        <h1 style={{ marginTop: 0 }}>Governance Analytics</h1>
        <p>
          Compliance findings from the active versions of submitted content.
        </p>
      </div>

      <div className="grid" style={{ marginBottom: '20px' }}>
        <div
          className="glass pad hoverlift"
          style={{ textAlign: 'center' }}
        >
          <h3 style={{ color: 'var(--c-300)', margin: 0 }}>
            Pending Reviews
          </h3>
          <div
            style={{
              fontSize: '54px',
              fontWeight: '800',
              marginTop: '10px',
            }}
          >
            {metrics.pendingReviews}
          </div>
        </div>

        <div
          className="glass pad hoverlift"
          style={{ textAlign: 'center' }}
        >
          <h3 style={{ color: 'var(--blocked)', margin: 0 }}>
            Active-Version Findings
          </h3>
          <div
            style={{
              fontSize: '54px',
              fontWeight: '800',
              marginTop: '10px',
            }}
          >
            {metrics.totalFindings}
          </div>
        </div>
      </div>

      <div className="glass pad hoverlift">
        <h3 style={{ marginBottom: '20px' }}>Most Violated Rules</h3>

        {metrics.ruleEntries.length === 0 ? (
          <p>No rule violations recorded yet.</p>
        ) : (
          <div style={{ display: 'grid', gap: '12px' }}>
            {metrics.ruleEntries.map(([rule, count]) => (
              <div
                key={rule}
                className="row"
                style={{
                  justifyContent: 'space-between',
                  paddingBottom: '12px',
                  borderBottom: '1px solid rgba(255,255,255,0.1)',
                }}
              >
                <span className="chip id">{rule}</span>
                <span style={{ fontWeight: 'bold', fontSize: '16px' }}>
                  {count} violations
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="glass pad hoverlift" style={{ marginTop: '20px' }}>
        <h3 style={{ marginBottom: '20px' }}>Findings by Category</h3>

        {Object.keys(metrics.categoryCounts).length === 0 ? (
          <p>No findings recorded yet.</p>
        ) : (
          <div style={{ display: 'grid', gap: '12px' }}>
            {Object.entries(metrics.categoryCounts).map(
              ([category, count]) => (
                <div
                  key={category}
                  className="row"
                  style={{
                    justifyContent: 'space-between',
                    paddingBottom: '12px',
                    borderBottom: '1px solid rgba(255,255,255,0.1)',
                  }}
                >
                  <span>{category.replaceAll('_', ' ')}</span>
                  <span style={{ fontWeight: 'bold' }}>{count}</span>
                </div>
              )
            )}
          </div>
        )}
      </div>
    </main>
  );
}
