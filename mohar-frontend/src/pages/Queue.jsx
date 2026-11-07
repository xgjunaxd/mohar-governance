import React, { useState, useEffect } from 'react';
import { getSubmissions, getSubmissionDetail, submitApproval } from '../services/api';
import { useRole } from '../context/RoleContext';

export default function Queue() {
  const { currentRole } = useRole();
  const [queue, setQueue] = useState([]);
  const [selectedSub, setSelectedSub] = useState(null);
  const [comment, setComment] = useState("");
  const [copied, setCopied] = useState(false);
  const [serverSeal, setServerSeal] = useState(null);

  const loadQueue = async () => {
    try { setQueue(await getSubmissions()); } catch (err) { console.error(err); }
  };
  useEffect(() => { loadQueue(); }, []);

  const handleSelect = async (id) => {
    try { 
      const details = await getSubmissionDetail(id);
      setSelectedSub(details); 
      setComment(""); 
      setCopied(false); 
      // Extract the seal from the audit log if it's already approved
      const approvalLog = details.audit_logs?.find(log => log.action.startsWith("approve_"));
      if (approvalLog && approvalLog.detail.includes("SHA-256 Seal: ")) {
          setServerSeal(approvalLog.detail.split("SHA-256 Seal: ")[1]);
      } else {
          setServerSeal(null);
      }
    } catch (err) { console.error(err); }
  };

  const handleAction = async (decision) => {
    if (currentRole === 'Creator') {
      alert("Access Denied: Creators cannot approve or reject submissions. Switch to Manager role.");
      return;
    }
    if (!selectedSub) return;
    try {
      const cleanComment = comment.replace(/[<>]/g, '').trim();
      const res = await submitApproval(selectedSub.submission.id, { role: currentRole, decision, comment: cleanComment });
      
      // Store the real cryptographic seal returned by the backend
      if (res.crypto_seal) {
          setServerSeal(res.crypto_seal);
      }
      
      await handleSelect(selectedSub.submission.id);
      loadQueue();
    } catch (err) { alert(err.message); }
  };

  // Fallback for UI if not approved yet, but we only print certificates for the real seal
  const displayHash = serverSeal || `PENDING-${selectedSub?.submission?.id?.substring(0, 8)}`;

  const downloadCertificate = () => {
    if (!selectedSub || !serverSeal) {
        alert("Cannot generate certificate: Missing cryptographic seal. Ensure the post is approved.");
        return;
    }
    const sub = selectedSub.submission;
    const latestBody = selectedSub.versions[0]?.body || "";
    const certText = [
      "============================================================",
      "          MOHAR BRAND GOVERNANCE COMPLIANCE SEAL            ",
      "============================================================",
      `Cryptographic Seal : #MHR-${serverSeal}`,
      `Submission ID      : ${sub.id}`,
      `Title              : ${sub.title}`,
      `Channel/Audience   : ${sub.channel} / ${sub.audience}`,
      `Final Status       : ${sub.status.toUpperCase()}`,
      `Approved Version   : v${sub.current_version}`,
      `Verified By Role   : ${currentRole}`,
      `Timestamp (UTC)    : ${new Date().toISOString()}`,
      "------------------------------------------------------------",
      "CERTIFIED COMPLIANT COPY:",
      latestBody,
      "============================================================"
    ].join("\n");

    const blob = new Blob([certText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Mohar-Audit-Certificate-${serverSeal.substring(0,8)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const latestVersion = selectedSub?.versions?.[0];
  const initialVersion = selectedSub?.versions?.[selectedSub.versions.length - 1];
  const hasMultipleVersions = selectedSub?.versions?.length > 1;

  return (
    <main>
      <div className="glass hero sheen hoverlift">
        <div className="row" style={{justifyContent: 'space-between'}}>
          <div>
            <h1 style={{marginTop: 0}}>Manager Approval Queue</h1>
            <p>Review version diffs, verify compliance, and issue cryptographic audit seals.</p>
          </div>
          <span className={`chip ${currentRole === 'Creator' ? 'review' : 'ready'}`}>
            Active Access: {currentRole} {currentRole === 'Creator' ? '(Read-Only)' : '(Sign-Off Enabled)'}
          </span>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 2fr' }}>
        <div className="glass pad">
          <h3>Submissions Ledger</h3>
          <div style={{display:'grid', gap:'12px', marginTop:'16px'}}>
            {queue.length === 0 ? <p>No items in queue.</p> : queue.map(item => (
              <div key={item.id} style={{paddingBottom: '16px', borderBottom: '1px solid rgba(255,255,255,0.1)'}}>
                <div style={{fontWeight: 'bold', marginBottom: '8px'}}>{item.title}</div>
                <div className="row" style={{marginBottom: '12px'}}>
                   <span className={`chip ${item.status === 'blocked' ? 'blocked' : item.status === 'needs_review' ? 'review' : 'ready'}`}>{item.status.replace('_', ' ')}</span>
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
              <div className="row" style={{justifyContent: 'space-between', marginBottom: '20px'}}>
                <h3 style={{margin: 0}}>{selectedSub.submission.title}</h3>
                <div className="row">
                  <span className="chip id">#MHR-{displayHash.substring(0, 8)}</span>
                  <span className={`chip ${selectedSub.submission.status === 'blocked' ? 'blocked' : selectedSub.submission.status === 'needs_review' ? 'review' : 'ready'}`}>
                    {selectedSub.submission.status.replace('_', ' ')}
                  </span>
                </div>
              </div>

              {hasMultipleVersions && (
                <div className="glass pad" style={{marginBottom: '18px', background: 'rgba(5,31,32,0.55)'}}>
                  <div className="label" style={{marginBottom: '10px'}}>Visual Audit Trail: Original (v1) vs Latest (v{latestVersion?.version_no})</div>
                  <div className="grid" style={{gridTemplateColumns: '1fr 1fr', gap: '12px'}}>
                    <div style={{padding: '12px', borderRadius: '12px', background: 'rgba(255,138,128,0.08)', border: '1px solid rgba(255,138,128,0.25)'}}>
                      <div style={{fontSize: '12px', color: 'var(--blocked)', fontWeight: '700', marginBottom: '6px'}}>v1 (Initial Draft)</div>
                      <p style={{fontSize: '13.5px', textDecoration: 'line-through', opacity: 0.85}}>{initialVersion?.body}</p>
                    </div>
                    <div style={{padding: '12px', borderRadius: '12px', background: 'rgba(125,240,176,0.08)', border: '1px solid rgba(125,240,176,0.25)'}}>
                      <div style={{fontSize: '12px', color: 'var(--ready)', fontWeight: '700', marginBottom: '6px'}}>v{latestVersion?.version_no} (Remediated Copy)</div>
                      <p style={{fontSize: '13.5px', color: 'var(--text)'}}>{latestVersion?.body}</p>
                    </div>
                  </div>
                </div>
              )}

              <div className="field">
                <label>Current Active Copy (v{latestVersion?.version_no})</label>
                <textarea readOnly value={latestVersion?.body || ""} />
              </div>

              {selectedSub.submission.status === 'approved' && (
                <div className="glass pad" style={{marginTop: '18px', border: '1px solid var(--ready)', background: 'rgba(125,240,176,0.07)'}}>
                  <div className="row" style={{justifyContent: 'space-between', marginBottom: '10px'}}>
                    <span className="chip ready">Mohar Certified Clean • Seal #MHR-{displayHash.substring(0,8)}</span>
                  </div>
                  <p style={{fontSize: '13.5px', marginBottom: '14px'}}>This asset has passed governance checks and is cleared for production distribution.</p>
                  <div className="row">
                    <button onClick={() => { navigator.clipboard.writeText(latestVersion?.body || ""); setCopied(true); }} className="btn primary">
                      {copied ? "Copied to Clipboard!" : "Copy Certified Text"}
                    </button>
                    <button onClick={downloadCertificate} className="btn">Download Audit Certificate (.txt)</button>
                  </div>
                </div>
              )}

              {currentRole !== 'Creator' && selectedSub.submission.status !== 'approved' ? (
                <div style={{marginTop: '20px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '18px'}}>
                  <div className="field">
                    <label>Manager Audit Comment (Max 300 chars)</label>
                    <input maxLength={300} type="text" placeholder="Official compliance sign-off note..." value={comment} onChange={e => setComment(e.target.value)} />
                  </div>
                  <div className="row" style={{marginTop: '16px'}}>
                    <button onClick={() => handleAction("approve")} className="btn primary">Approve & Issue Seal</button>
                    <button onClick={() => handleAction("reject")} className="btn warn">Reject</button>
                    <button onClick={() => handleAction("request_changes")} className="btn">Request Changes</button>
                  </div>
                </div>
              ) : currentRole === 'Creator' && selectedSub.submission.status !== 'approved' ? (
                <div className="glass pad" style={{marginTop: '20px', background: 'rgba(255,210,122,0.08)'}}>
                  <span className="chip review">Protected Admin Route: Switch role to Manager or Reviewer in the top bar to approve or reject.</span>
                </div>
              ) : null}
            </div>
          ) : <p style={{textAlign: 'center', marginTop: '40px'}}>Select a submission from the ledger to inspect version diffs and issue approvals.</p>}
        </div>
      </div>
    </main>
  );
}