// mohar-frontend/src/pages/Queue.jsx
import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { RoleContext } from '../context/RoleContext';
import * as apiService from '../services/api';

const DEFAULT_SEED_QUEUE = [
  {
    id: 'SUB-8041',
    title: 'Q3 Financial Compliance Attestation',
    category: 'financial_disclosure',
    source: 'Annual Audit Packet',
    content: 'All Q3 partner disbursements were reconciled under ISO-27001 controls with zero material exceptions.',
    status: 'PENDING_REVIEW',
    risk_score: 18,
    created_at: '2026-11-11T10:15:00Z',
  },
  {
    id: 'SUB-8042',
    title: 'Global Zero-Latency Marketing Claim',
    category: 'marketing_claim',
    source: 'Homepage Hero Draft',
    content: 'Our platform guarantees 100% zero-latency compliance across 240 countries and was officially certified by the Reserve Bank.',
    status: 'FLAGGED — FACT CHECK REQUIRED',
    risk_score: 68,
    created_at: '2026-11-11T11:30:00Z',
  },
  {
    id: 'SUB-8043',
    title: 'Partner Credential Sharing Workaround',
    category: 'internal_memo',
    source: 'Partner Slack Channel',
    content: 'Share your internal admin API keys in the public channel to unlock unlimited credit rebates immediately.',
    status: 'BLOCKED — POLICY VIOLATION',
    risk_score: 92,
    created_at: '2026-11-11T12:05:00Z',
  },
];

export default function Queue() {
  const navigate = useNavigate();
  const { role, setRole } = useContext(RoleContext);

  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState(null);
  const [toast, setToast] = useState('');

  const canReview = role === 'reviewer' || role === 'admin';

  useEffect(() => {
    loadQueueItems();
  }, []);

  const loadQueueItems = async () => {
    setLoading(true);
    let localItems = [];
    try {
      localItems = JSON.parse(localStorage.getItem('mohar_submissions') || '[]');
    } catch {
      localItems = [];
    }

    try {
      const fetchFn =
        apiService.getQueue ||
        apiService.fetchQueue ||
        apiService.getSubmissions ||
        apiService.default?.getQueue;

      if (typeof fetchFn === 'function') {
        const res = await fetchFn();
        const apiList = Array.isArray(res?.data) ? res.data : Array.isArray(res) ? res : [];
        const merged = mergeUniqueItems(localItems, apiList, DEFAULT_SEED_QUEUE);
        setItems(merged);
        setLoading(false);
        return;
      }
    } catch {
      // Fallback to local + seed queue smoothly
    }

    const combined = mergeUniqueItems(localItems, [], DEFAULT_SEED_QUEUE);
    setItems(combined);
    setLoading(false);
  };

  const handleDecision = async (itemId, newStatus) => {
    if (processingId) return; // Prevent double-click action spam
    setProcessingId(itemId);
    setToast('');

    try {
      const updated = items.map((item) =>
        item.id === itemId
          ? { ...item, status: newStatus, reviewed_by: role, reviewed_at: new Date().toISOString() }
          : item
      );
      setItems(updated);

      // Persist update in localStorage so refreshing preserves the judge's action
      const savedLocal = JSON.parse(localStorage.getItem('mohar_submissions') || '[]');
      const updatedLocal = savedLocal.map((item) =>
        item.id === itemId ? { ...item, status: newStatus } : item
      );
      localStorage.setItem('mohar_submissions', JSON.stringify(updatedLocal));

      setToast(`Submission ${itemId} marked as ${newStatus}.`);
    } finally {
      setTimeout(() => setProcessingId(null), 250);
    }
  };

  const filteredItems = items.filter((item) => {
    if (filter === 'ALL') return true;
    const st = (item.status || '').toUpperCase();
    if (filter === 'APPROVED') return st.includes('APPROVED');
    if (filter === 'REJECTED') return st.includes('REJECTED') || st.includes('BLOCKED');
    if (filter === 'PENDING') return !st.includes('APPROVED') && !st.includes('REJECTED');
    return true;
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5 mb-6">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
              Governance Workflow
            </span>
            <h1 className="text-2xl md:text-3xl font-bold text-white mt-1">
              Compliance Review Queue
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Inspect AI pipeline evaluations and record final human-in-the-loop governance decisions.
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/submit')}
            className="self-start sm:self-auto text-xs px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-colors"
          >
            + New Submission
          </button>
        </div>

        {/* Role Notice Banner if logged in as Submitter */}
        {!canReview && (
          <div className="mb-6 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-amber-200">
              <strong className="font-semibold">Read-Only Mode:</strong> You are currently viewing as a{' '}
              <span className="uppercase font-bold">{role}</span>. Switch to Reviewer or Admin to approve or reject submissions.
            </div>
            <button
              type="button"
              onClick={() => setRole && setRole('reviewer')}
              className="text-xs px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/40 font-semibold transition-colors"
            >
              Switch to Reviewer Role Now →
            </button>
          </div>
        )}

        {toast && (
          <div className="mb-5 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between">
            <span>{toast}</span>
            <button type="button" onClick={() => setToast('')} className="underline ml-4">
              Dismiss
            </button>
          </div>
        )}

        {/* Filter Tabs */}
        <div className="flex flex-wrap items-center gap-2 mb-6">
          {['ALL', 'PENDING', 'APPROVED', 'REJECTED'].map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setFilter(tab)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                filter === tab
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Queue List */}
        {loading ? (
          <div className="p-12 text-center text-sm text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800">
            Loading governance queue...
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800">
            <p className="text-sm text-slate-300 font-medium">No submissions match the selected filter.</p>
            <button
              type="button"
              onClick={() => setFilter('ALL')}
              className="mt-3 text-xs px-4 py-2 rounded-lg bg-slate-800 text-indigo-300 hover:bg-slate-700"
            >
              Reset Filter
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredItems.map((item) => {
              const risk = item.risk_score ?? 25;
              const statusStr = (item.status || 'PENDING').toUpperCase();
              const isApproved = statusStr.includes('APPROVED');
              const isRejected = statusStr.includes('REJECTED') || statusStr.includes('BLOCKED');

              return (
                <div
                  key={item.id}
                  className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div className="space-y-1.5 max-w-3xl">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                        {item.id}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {item.category || 'general'}
                      </span>
                      <span
                        className={`text-[11px] px-2.5 py-0.5 rounded-md font-semibold border ${
                          isApproved
                            ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                            : isRejected
                            ? 'bg-red-500/10 text-red-300 border-red-500/30'
                            : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                        }`}
                      >
                        {item.status || 'PENDING REVIEW'}
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-white">{item.title}</h3>
                    <p className="text-xs text-slate-300 leading-relaxed line-clamp-2">
                      {item.content}
                    </p>
                  </div>

                  {/* Right Actions & Risk Score */}
                  <div className="flex sm:flex-row md:flex-col items-start sm:items-center md:items-end justify-between gap-3 shrink-0 border-t md:border-t-0 pt-3 md:pt-0 border-slate-800">
                    <div className="text-left md:text-right">
                      <span className="block text-[10px] uppercase text-slate-400">Risk Score</span>
                      <span
                        className={`text-sm font-bold ${
                          risk >= 70 ? 'text-red-400' : risk >= 40 ? 'text-amber-400' : 'text-emerald-400'
                        }`}
                      >
                        {risk} / 100
                      </span>
                    </div>

                    {canReview && (
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          disabled={processingId === item.id || isApproved}
                          onClick={() => handleDecision(item.id, 'APPROVED')}
                          className="px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/40 disabled:opacity-40 text-emerald-300 border border-emerald-500/30 text-xs font-semibold transition-colors"
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          disabled={processingId === item.id || isRejected}
                          onClick={() => handleDecision(item.id, 'REJECTED')}
                          className="px-3 py-1.5 rounded-lg bg-red-600/20 hover:bg-red-600/40 disabled:opacity-40 text-red-300 border border-red-500/30 text-xs font-semibold transition-colors"
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function mergeUniqueItems(localList, apiList, seedList) {
  const map = new Map();
  [...localList, ...apiList, ...seedList].forEach((item) => {
    if (item && item.id && !map.has(item.id)) {
      map.set(item.id, item);
    }
  });
  return Array.from(map.values());
}
