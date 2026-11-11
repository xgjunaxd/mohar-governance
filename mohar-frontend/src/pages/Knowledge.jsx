import React, { useState, useEffect } from 'react';
import { getWorkspace, getConflicts, getFactVersions, updateFact, createFact, updateRule } from '../services/api';
import { useRole } from '../context/RoleContext';

const TODAY = new Date(new Date().toDateString());
function daysLeft(iso) {
  if (!iso) return null;
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime()) ? null : Math.round((d - TODAY) / 86400000);
}
function stateOf(fact) {
  if (String(fact.status).toLowerCase() === 'expired') return { label: 'Expired', cls: 'blocked' };
  const left = daysLeft(fact.expires_on);
  if (left === null) return { label: 'No expiry', cls: 'info' };
  if (left < 0) return { label: 'Expired', cls: 'blocked' };
  if (left <= 30) return { label: `Expires in ${left}d`, cls: 'review' };
  return { label: `Valid until ${fact.expires_on}`, cls: 'ready' };
}
const clean = (s) => s.replace(/[<>]/g, '');

export default function Knowledge() {
  const { currentRole } = useRole();
  const [facts, setFacts] = useState([]);
  const [rules, setRules] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(null); // { type, lines[] }
  const [editing, setEditing] = useState(null); // fact id or 'new'
  const [form, setForm] = useState({});
  const [history, setHistory] = useState({}); // fact id -> versions[]
  const [busy, setBusy] = useState(false);
  const [ruleEdit, setRuleEdit] = useState(null);
  const [ruleForm, setRuleForm] = useState({});

  const load = async () => {
    try {
      const ws = await getWorkspace();
      setFacts(ws.data.facts || []);
      setRules(ws.data.rules || []);
      const c = await getConflicts();
      setConflicts(c.conflicts || []);
      setError('');
    } catch (err) { setError(err.message); }
  };
  useEffect(() => { if (currentRole === 'Reviewer') load(); }, [currentRole]); // eslint-disable-line react-hooks/exhaustive-deps

  if (currentRole !== 'Reviewer') {
    return (
      <main>
        <div className="glass hero sheen">
          <h1>Knowledge Workspace</h1>
          <p>Only Reviewers can edit rules and facts. Sign in as a Reviewer to manage the knowledge base.</p>
        </div>
      </main>
    );
  }

  const startEdit = (fact) => {
    setEditing(fact.id); setNotice(null);
    setForm({
      approved_text: fact.approved_text || '', source: fact.source || '', owner: fact.owner || '',
      valid_from: fact.valid_from || '', expires_on: fact.expires_on || '', topic: fact.topic || '',
      status: fact.status || 'active', change_note: '', clear_expiry: false,
    });
  };
  const startNew = () => {
    setEditing('new'); setNotice(null);
    setForm({ id: '', approved_text: '', source: '', owner: '', valid_from: '', expires_on: '', topic: '', status: 'active' });
  };

  const save = async (e) => {
    e.preventDefault();
    setBusy(true); setNotice(null);
    try {
      let res;
      if (editing === 'new') {
        res = await createFact({
          id: form.id.trim(), approved_text: clean(form.approved_text.trim()), source: clean(form.source.trim()),
          owner: clean(form.owner.trim()), valid_from: form.valid_from || null, expires_on: form.expires_on || null,
          status: 'active', topic: form.topic.trim() || null,
        });
      } else {
        const body = {
          approved_text: clean(form.approved_text.trim()), source: clean(form.source.trim()), owner: clean(form.owner.trim()),
          valid_from: form.valid_from || null, topic: form.topic.trim() || null, status: form.status,
          change_note: clean(form.change_note.trim()) || null,
        };
        if (form.clear_expiry) body.clear_expiry = true; else body.expires_on = form.expires_on || null;
        res = await updateFact(editing, body);
      }
      const lines = res.warnings && res.warnings.length ? res.warnings : [];
      setNotice(lines.length
        ? { type: 'warn', lines: ['Saved, but there is a conflict:', ...lines] }
        : { type: 'ok', lines: [editing === 'new' ? 'Fact added.' : `Saved as version ${res.new_version}. The previous version is kept in history.`] });
      setEditing(null);
      setHistory({});
      await load();
    } catch (err) { setNotice({ type: 'error', lines: [err.message] }); }
    finally { setBusy(false); }
  };

  const toggleHistory = async (id) => {
    if (history[id]) { setHistory((h) => { const n = { ...h }; delete n[id]; return n; }); return; }
    try { const r = await getFactVersions(id); setHistory((h) => ({ ...h, [id]: r.history })); }
    catch (err) { setNotice({ type: 'error', lines: [err.message] }); }
  };

  const saveRule = async (e) => {
    e.preventDefault(); setBusy(true);
    try {
      await updateRule(ruleEdit, { text: clean(ruleForm.text.trim()), severity: ruleForm.severity });
      setRuleEdit(null); setNotice({ type: 'ok', lines: ['Rule saved (new rule version).'] }); await load();
    } catch (err) { setNotice({ type: 'error', lines: [err.message] }); }
    finally { setBusy(false); }
  };

  const bannerColor = { ok: 'var(--ready)', warn: 'var(--review)', error: 'var(--blocked)' };

  return (
    <main>
      <div className="glass hero sheen">
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <div>
            <h1 style={{ margin: 0 }}>Knowledge Workspace</h1>
            <p style={{ margin: '8px 0 0' }}>Edit facts and rules. Every change keeps the old version, and conflicts are flagged straight away.</p>
          </div>
          <button className="btn primary" onClick={startNew}>Add a fact</button>
        </div>
      </div>

      {error && <div className="glass pad" role="alert" style={{ marginBottom: '18px', color: 'var(--blocked)' }}>{error}</div>}
      {notice && (
        <div className="glass pad" role="alert" style={{ marginBottom: '18px', color: bannerColor[notice.type] }}>
          {notice.lines.map((l, i) => <div key={i}>{l}</div>)}
        </div>
      )}
      {conflicts.length > 0 && (
        <div className="glass pad" style={{ marginBottom: '18px', border: '1px solid var(--review)' }}>
          <div className="label" style={{ color: 'var(--review)' }}>Conflicting facts ({conflicts.length})</div>
          {conflicts.map((c) => (
            <div key={`${c.fact_a}-${c.fact_b}`} style={{ marginTop: '10px', fontSize: '14px' }}>
              <strong>{c.fact_a}</strong>: {c.text_a}<br />
              <strong>{c.fact_b}</strong>: {c.text_b}<br />
              <span style={{ color: 'var(--text-2)' }}>{c.message} Expire or correct one of them.</span>
            </div>
          ))}
        </div>
      )}

      {editing && (
        <form onSubmit={save} className="glass pad" style={{ marginBottom: '24px' }}>
          <h3 style={{ marginTop: 0 }}>{editing === 'new' ? 'Add a fact' : `Edit ${editing}`}</h3>
          {editing === 'new' && (
            <div className="field"><label>Fact ID (e.g. F-011)</label>
              <input required pattern="[A-Za-z0-9_-]{1,40}" value={form.id} onChange={(e) => setForm({ ...form, id: e.target.value })} /></div>
          )}
          <div className="field"><label>Approved text</label>
            <textarea required rows="3" maxLength={1000} value={form.approved_text} onChange={(e) => setForm({ ...form, approved_text: e.target.value })} /></div>
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
            <div className="field"><label>Source</label><input required maxLength={300} value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} /></div>
            <div className="field"><label>Owner</label><input required maxLength={100} value={form.owner} onChange={(e) => setForm({ ...form, owner: e.target.value })} /></div>
            <div className="field"><label>Valid from</label><input type="date" value={form.valid_from} onChange={(e) => setForm({ ...form, valid_from: e.target.value })} /></div>
            <div className="field"><label>Expires on</label><input type="date" disabled={form.clear_expiry} value={form.expires_on} onChange={(e) => setForm({ ...form, expires_on: e.target.value })} /></div>
            <div className="field"><label>Topic (same topic = checked for conflicts)</label><input maxLength={60} placeholder="e.g. upi_daily_limit" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} /></div>
            {editing !== 'new' && (
              <div className="field"><label>Status</label>
                <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                  <option value="active">Active</option><option value="draft">Draft</option><option value="expired">Expired</option>
                </select></div>
            )}
          </div>
          {editing !== 'new' && (
            <>
              <label style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '14px' }}>
                <input type="checkbox" checked={form.clear_expiry} onChange={(e) => setForm({ ...form, clear_expiry: e.target.checked })} /> Remove the expiry date
              </label>
              <div className="field"><label>What changed and why (saved in history)</label>
                <input maxLength={300} value={form.change_note} onChange={(e) => setForm({ ...form, change_note: e.target.value })} /></div>
            </>
          )}
          <div className="row">
            <button type="submit" className="btn primary" disabled={busy}>{busy ? 'Saving...' : 'Save'}</button>
            <button type="button" className="btn" onClick={() => setEditing(null)}>Cancel</button>
          </div>
        </form>
      )}

      <h2 className="sec">Approved Facts</h2>
      <div className="grid">
        {facts.map((f) => {
          const st = stateOf(f);
          return (
            <article key={f.id} className="glass pad hoverlift">
              <div className="row" style={{ marginBottom: '10px' }}>
                <span className="chip id">{f.id}</span>
                <span className={`chip ${st.cls}`}>{st.label}</span>
                <span className="chip info">v{f.version || 1}</span>
              </div>
              <p style={{ margin: '8px 0 12px' }}>{f.approved_text}</p>
              <div className="label">Source: {f.source}</div>
              {f.topic && <div className="label" style={{ marginTop: '4px' }}>Topic: {f.topic}</div>}
              <div className="row" style={{ marginTop: '14px' }}>
                <button className="btn" onClick={() => startEdit(f)}>Edit</button>
                <button className="btn" onClick={() => toggleHistory(f.id)}>{history[f.id] ? 'Hide history' : 'History'}</button>
              </div>
              {history[f.id] && (
                <div style={{ marginTop: '14px', display: 'grid', gap: '8px' }}>
                  {history[f.id].length === 0 && <span style={{ fontSize: '13px', color: 'var(--text-2)' }}>No earlier versions yet.</span>}
                  {history[f.id].map((v) => (
                    <div key={v.id || v.version} style={{ fontSize: '13px', padding: '10px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.1)' }}>
                      <strong>v{v.version}</strong> · changed by {v.changed_by || 'unknown'}{v.archived_at ? ` · ${new Date(v.archived_at).toLocaleDateString()}` : ''}
                      <div style={{ color: 'var(--text-2)', marginTop: 4 }}>{v.approved_text}{v.expires_on ? ` (expired/expires ${v.expires_on})` : ''}</div>
                      {v.change_note && <div style={{ marginTop: 4 }}>Note: {v.change_note}</div>}
                    </div>
                  ))}
                </div>
              )}
            </article>
          );
        })}
      </div>

      <h2 className="sec" style={{ marginTop: '40px' }}>Brand Rules</h2>
      <div className="grid">
        {rules.map((r) => (
          <article key={r.id} className="glass pad hoverlift">
            <div className="row" style={{ marginBottom: '10px' }}>
              <span className="chip id">{r.id}</span>
              <span className={`chip ${r.severity === 'high' ? 'blocked' : r.severity === 'medium' ? 'review' : 'ready'}`}>{r.severity}</span>
              <span className="chip info">v{r.version || 1}</span>
            </div>
            {ruleEdit === r.id ? (
              <form onSubmit={saveRule}>
                <div className="field"><textarea rows="3" required maxLength={1000} value={ruleForm.text} onChange={(e) => setRuleForm({ ...ruleForm, text: e.target.value })} /></div>
                <div className="field"><select value={ruleForm.severity} onChange={(e) => setRuleForm({ ...ruleForm, severity: e.target.value })}>
                  <option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></div>
                <div className="row"><button className="btn primary" disabled={busy}>Save</button><button type="button" className="btn" onClick={() => setRuleEdit(null)}>Cancel</button></div>
              </form>
            ) : (
              <>
                <p style={{ margin: '8px 0 12px' }}>{r.text}</p>
                <button className="btn" onClick={() => { setRuleEdit(r.id); setRuleForm({ text: r.text, severity: r.severity }); }}>Edit</button>
              </>
            )}
          </article>
        ))}
      </div>
    </main>
  );
}
