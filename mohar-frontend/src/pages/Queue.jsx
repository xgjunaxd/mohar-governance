import React, { useState, useEffect, useMemo } from 'react';
import { getSubmissions, getSubmissionDetail, submitApproval } from '../services/api';
import { useRole } from '../context/RoleContext';

// Statuses a Manager/Reviewer may approve. 'blocked' (unresolved high-severity findings) never can be.
const APPROVABLE = ['ready_for_approval', 'needs_review'];

const FILTERS = [
  { key: 'all', label: 'All', match: () => true },
  { key: 'attention', label: 'Awaiting sign-off', match: (s) => APPROVABLE.includes(s) },
  { key: 'blocked', label: 'Blocked', match: (s) => s === 'blocked' },
  { key: 'approved', label: 'Approved', match: (s) => s === 'approved' },
];

const chipFor = (status) => {
  if (status === 'blocked' || status === 'rejected') return 'blocked';
  if (status === 'needs_review' || status === 'changes_requested') return 'review';
  return 'ready';
};
const pretty = (status = '') => status.replace(/_/g, ' ');

/** Word-level diff (LCS) so the manager sees exactly what changed between two versions. */
function diffWords(oldText = '', newText = '') {
  const a = oldText.split(/(\s+)/);
  const b = newText.split(/(\s+)/);
  const n = a.length, m = b.length;
  if (n * m > 400000) return [{ type: 'del', text: oldText }, { type: 'add', text: newText }];
  const dp = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const out = [];
  const push = (type, text) => {
    const last = out[out.length - 1];
    if (last && last.type === type) last.text += text; else out.push({ type, text });
  };
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) { push('same', a[i]); i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) { push('del', a[i]); i++; }
    else { push('add', b[j]); j++; }
  }
  while (i < n) push('del', a[i++]);
  while (j < m) push('add', b[j++]);
  return out;
}

async function sha256Hex(text) {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) return null; // e.g. page opened over plain http
  const digest = await subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('');
}

const SEAL_MARK = 'SHA-256 Seal: ';
const bannerStyle = (type) => ({
  padding: '12px 16px', borderRadius: '14px', marginBottom: '18px', fontSize: '14px',
  border: '1px solid currentColor', background: 'rgba(5,31,32,0.55)',
  color: type === 'error' ? 'var(--blocked)' : type === 'ok' ? 'var(--ready)' : 'var(--review)',
});
const disabledStyle = (disabled) => (disabled ? { opacity: 0.5, cursor: 'not-allowed' } : {});

export default function Queue() {
  const { currentRole } = useRole();
  const [queue, setQueue] = useState([]);
  const [queueError, setQueueError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [selectedSub, setSelectedSub] = useState(null);
  const [comment, setComment] = useState('');
  const [copied, setCopied] = useState(false);
  const [message, setMessage] = useState(null); // { type: 'error' | 'ok' | 'warn', text }
  const [compareNo, setCompareNo] = useState(null);
  const [verifyState, setVerifyState] = useState(null); // null | 'ok' | 'bad' | 'unavailable'
  const [busy, setBusy] = useState(false);

  const loadQueue = async () => {
    try { setQueue(await getSubmissions()); setQueueError(null); }
    catch (err) { setQueueError(err.message || 'Could not load the queue.'); }
  };
  useEffect(() => { loadQueue(); }, []);

  const handleSelect = async (id) => {
    try {
      const details = await getSubmissionDetail(id);
      setSelectedSub(details);
      setComment('');
      setCopied(false);
      const versions = details.versions || [];
      setCompareNo(versions.length > 1 ? versions[1].version_no : null); // default: previous version
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Could not load this submission.' });
    }
  };

  // ---- Everything about the approval is DERIVED from the server's audit log (no duplicate state to go stale) ----
  const sub = selectedSub?.submission;
  const versions = selectedSub?.versions || [];
  const latestVersion = versions[0];
  const approvalLog = (selectedSub?.audit_logs || []).find((l) => /^approve_v\d+$/.test(l.action || ''));
  const approvedVersionNo = approvalLog ? Number(approvalLog.action.match(/^approve_v(\d+)$/)[1]) : null;
  const approvedVersion = versions.find((v) => v.version_no === approvedVersionNo);
  const seal = approvalLog && (approvalLog.detail || '').includes(SEAL_MARK)
    ? approvalLog.detail.split(SEAL_MARK)[1].trim() : null;
  const approverComment = approvalLog ? (approvalLog.detail || '').split(' | ' + SEAL_MARK)[0] : '';
  const isApproved = sub?.status === 'approved';
  const canApprove = sub && APPROVABLE.includes(sub.status);

  // Automatically re-check the seal whenever an approved submission is opened.
  useEffect(() => {
    let cancelled = false;
    setVerifyState(null);
    if (isApproved && seal && approvedVersion) {
      sha256Hex(approvedVersion.body).then((hex) => {
        if (!cancelled) setVerifyState(hex === null ? 'unavailable' : hex === seal ? 'ok' : 'bad');
      });
    }
    return () => { cancelled = true; };
  }, [selectedSub]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAction = async (decision) => {
    if (currentRole !== 'Manager') {
      setMessage({ type: 'error', text: 'Access denied: only Managers can approve, reject or request changes. Sign in as a Manager.' });
      return;
    }
    if (!selectedSub) return;
    setBusy(true);
    setMessage(null);
    try {
      const cleanComment = comment.replace(/[<>]/g, '').trim();
      await submitApproval(sub.id, { role: currentRole, decision, comment: cleanComment });
      await handleSelect(sub.id);
      loadQueue();
      setMessage({
        type: 'ok',
        text: decision === 'approve' ? 'Approved. The server issued a SHA-256 seal for this version.' : `Submission marked: ${pretty(decision)}.`,
      });
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'The action failed.' });
    } finally {
      setBusy(false);
    }
  };

  const diff = useMemo(() => {
    const from = versions.find((v) => v.version_no === compareNo);
    return from && latestVersion ? diffWords(from.body, latestVersion.body) : [];
  }, [selectedSub, compareNo]); // eslint-disable-line react-hooks/exhaustive-deps

  const downloadCertificate = () => {
    if (!seal || !approvedVersion) {
      setMessage({ type: 'error', text: 'Cannot generate a certificate: this submission has no approval seal yet.' });
      return;
    }
    const certText = [
      '============================================================',
      '          MOHAR BRAND GOVERNANCE COMPLIANCE SEAL            ',
      '============================================================',
      `SHA-256 Seal       : ${seal}`,
      `Seal ID            : #MHR-${seal.substring(0, 8)}`,
      `Submission ID      : ${sub.id}`,
      `Title              : ${sub.title}`,
      `Channel/Audience   : ${sub.channel} / ${sub.audience}`,
      `Approved Version   : v${approvedVersionNo}`,
      `Approved By (role) : ${approvalLog.role}`,
      `Approved At (UTC)  : ${approvalLog.created_at}`,
      `Approver Comment   : ${approverComment || '-'}`,
      '------------------------------------------------------------',
      'APPROVED TEXT:',
      approvedVersion.body,
      '============================================================',
      'The seal is the SHA-256 hash of the approved text above.',
      'If the text changes, the hash no longer matches.',
    ].join('\n');

    const blob = new Blob([certText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Mohar-Audit-Certificate-${seal.substring(0, 8)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const visibleQueue = queue.filter((item) => FILTERS.find((f) => f.key === filter).match(item.status));
  const tidyDetail = (text = '') => text.replace(/\| SHA-256 Seal: ([0-9a-f]{8})[0-9a-f]*/, '| Seal #MHR-$1');

  return (
    <main>
      <div className="glass hero sheen hoverlift">
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <div>
            <h1 style={{ marginTop: 0 }}>Manager Approval Queue</h1>
            <p>Review version diffs, verify compliance, and issue SHA-256 audit seals.</p>
          </div>
          <span className={`chip ${currentRole !== 'Manager' ? 'review' : 'ready'}`}>
            Active Access: {currentRole} {currentRole !== 'Manager' ? '(Read-Only)' : '(Sign-Off Enabled)'}
          </span>
        </div>
      </div>

      {message && <div style={bannerStyle(message.type)} role="alert">{message.text}</div>}
      {queueError && (
        <div style={bannerStyle('error')} role="alert">
          Could not load the queue: {queueError}{' '}
          <button className="btn" onClick={loadQueue} style={{ marginLeft: 12 }}>Retry</button>
        </div>
      )}

      <div className="grid" style={{ gridTemplateColumns: '1fr 2fr' }}>
        <div className="glass pad">
          <h3>Submissions Ledger</h3>
          <div className="row" style={{ margin: '12px 0', flexWrap: 'wrap' }}>
            {FILTERS.map((f) => (
              <button key={f.key} className="btn" aria-pressed={filter === f.key} onClick={() => setFilter(f.key)}
                style={{ minHeight: 34, padding: '0 14px', opacity: filter === f.key ? 1 : 0.65 }}>{f.label}</button>
            ))}
          </div>
          <div style={{ display: 'grid', gap: '12px', marginTop: '16px' }}>
            {visibleQueue.length === 0 ? <p>No items in this view.</p> : visibleQueue.map((item) => (
              <div key={item.id} style={{ paddingBottom: '16px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>{item.title}</div>
                <div className="row" style={{ marginBottom: '12px' }}>
                  <span className={`chip ${chipFor(item.status)}`}>{pretty(item.status)}</span>
                  <span className="chip id">v{item.current_version || 1}</span>
                </div>
                <button onClick={() => handleSelect(item.id)} className="btn">View Details</button>
              </div>
            ))}
          </div>
        </div>

        <div className="glass pad">
          {selectedSub ? (
            <div>
              <div className="row" style={{ justifyContent: 'space-between', marginBottom: '20px' }}>
                <h3 style={{ margin: 0 }}>{sub.title}</h3>
                <div className="row">
                  {isApproved && seal && <span className="chip id">#MHR-{seal.substring(0, 8)}</span>}
                  <span className={`chip ${chipFor(sub.status)}`}>{pretty(sub.status)}</span>
                </div>
              </div>

              {versions.length > 1 && (
                <div className="glass pad" style={{ marginBottom: '18px', background: 'rgba(5,31,32,0.55)' }}>
                  <div className="row" style={{ justifyContent: 'space-between', marginBottom: '10px' }}>
                    <div className="label">What changed: v{compareNo} &rarr; v{latestVersion?.version_no}</div>
                    <select aria-label="Compare with version" value={compareNo ?? ''} onChange={(e) => setCompareNo(Number(e.target.value))} style={{ maxWidth: 170 }}>
                      {versions.slice(1).map((v) => <option key={v.id} value={v.version_no}>Compare with v{v.version_no}</option>)}
                    </select>
                  </div>
                  <p style={{ fontSize: '14px', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                    {diff.map((part, i) => part.type === 'same'
                      ? <span key={i}>{part.text}</span>
                      : <span key={i} style={part.type === 'add'
                        ? { background: 'rgba(125,240,176,0.18)', borderRadius: 4, padding: '0 2px' }
                        : { background: 'rgba(255,138,128,0.18)', textDecoration: 'line-through', borderRadius: 4, padding: '0 2px' }}>{part.text}</span>)}
                  </p>
                </div>
              )}

              <div className="field">
                <label>Current Active Copy (v{latestVersion?.version_no})</label>
                <textarea readOnly value={latestVersion?.body || ''} />
              </div>

              {isApproved && seal && (
                <div className="glass pad" style={{ marginTop: '18px', border: '1px solid var(--ready)', background: 'rgba(125,240,176,0.07)' }}>
                  <div className="row" style={{ marginBottom: '10px', flexWrap: 'wrap' }}>
                    <span className="chip ready">Mohar Certified &bull; Seal #MHR-{seal.substring(0, 8)}</span>
                    {verifyState === 'ok' && <span className="chip ready">Verified: text matches the seal</span>}
                    {verifyState === 'bad' && <span className="chip blocked">NOT verified: text does not match the seal</span>}
                    {verifyState === 'unavailable' && <span className="chip review">Verification unavailable in this browser context</span>}
                  </div>
                  <p style={{ fontSize: '13.5px', marginBottom: '10px' }}>
                    Approved v{approvedVersionNo} by {approvalLog.role} on {new Date(approvalLog.created_at).toLocaleString()}.
                    {approverComment ? ` Comment: "${approverComment}"` : ''}
                  </p>
                  <p style={{ fontSize: '12px', marginBottom: '14px', wordBreak: 'break-all', fontFamily: 'ui-monospace, Menlo, monospace' }}>SHA-256: {seal}</p>
                  <div className="row" style={{ flexWrap: 'wrap' }}>
                    <button onClick={() => { navigator.clipboard.writeText(approvedVersion?.body || ''); setCopied(true); }} className="btn primary">
                      {copied ? 'Copied to Clipboard!' : 'Copy Certified Text'}
                    </button>
                    <button onClick={downloadCertificate} className="btn">Download Audit Certificate (.txt)</button>
                  </div>
                </div>
              )}

              {currentRole === 'Manager' && !isApproved ? (
                <div style={{ marginTop: '20px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '18px' }}>
                  <div className="field">
                    <label htmlFor="audit-comment">Manager Audit Comment (Max 300 chars)</label>
                    <input id="audit-comment" maxLength={300} type="text" placeholder="Official compliance sign-off note..." value={comment} onChange={(e) => setComment(e.target.value)} />
                  </div>
                  {!canApprove && (
                    <p style={{ fontSize: '13px', color: 'var(--review)', marginBottom: 10 }}>
                      Approval is disabled while the status is &ldquo;{pretty(sub.status)}&rdquo;. Blocked submissions need their high-severity findings resolved first.
                    </p>
                  )}
                  <div className="row" style={{ marginTop: '16px' }}>
                    <button onClick={() => handleAction('approve')} disabled={!canApprove || busy} className="btn primary" style={disabledStyle(!canApprove || busy)}>
                      {busy ? 'Working...' : 'Approve & Issue Seal'}
                    </button>
                    <button onClick={() => handleAction('reject')} disabled={busy} className="btn warn" style={disabledStyle(busy)}>Reject</button>
                    <button onClick={() => handleAction('request_changes')} disabled={busy} className="btn" style={disabledStyle(busy)}>Request Changes</button>
                  </div>
                </div>
              ) : currentRole !== 'Manager' && !isApproved ? (
                <div className="glass pad" style={{ marginTop: '20px', background: 'rgba(255,210,122,0.08)' }}>
                  <span className="chip review">Only Managers can approve or reject. Sign in as a Manager to continue.</span>
                </div>
              ) : null}

              <div style={{ marginTop: '24px' }}>
                <div className="label" style={{ marginBottom: '10px' }}>Audit log</div>
                <div style={{ display: 'grid', gap: '10px' }}>
                  {(selectedSub.audit_logs || []).length === 0 && <p>No audit entries yet.</p>}
                  {(selectedSub.audit_logs || []).map((log) => (
                    <div key={log.id} style={{ padding: '10px 12px', borderRadius: 12, background: 'rgba(5,31,32,0.45)', border: '1px solid rgba(255,255,255,0.08)', fontSize: '13.5px' }}>
                      <strong>{log.actor_email || log.role}</strong> <span style={{ color: 'var(--text-2)' }}>({log.role})</span> &middot; {(log.action || '').replace(/_/g, ' ')}
                      <span style={{ float: 'right', color: 'var(--text-2)' }}>{new Date(log.created_at).toLocaleString()}</span>
                      <div style={{ color: 'var(--text-2)', marginTop: 4, wordBreak: 'break-word' }}>{tidyDetail(log.detail)}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : <p style={{ textAlign: 'center', marginTop: '40px' }}>Select a submission from the ledger to inspect version diffs and issue approvals.</p>}
        </div>
      </div>
    </main>
  );
}
