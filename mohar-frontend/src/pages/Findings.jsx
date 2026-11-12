import React, { useState, useEffect } from 'react';
import Skeleton from '../components/Skeleton';
import { useParams } from 'react-router-dom';
import { getSubmissionDetail, recordDecision, resubmitPost } from '../services/api';
import { useRole } from '../context/RoleContext';
import { canApplyFix, applyFixToText } from '../utils/fixes';

export default function Findings() {
  const { id } = useParams();
  const { currentRole } = useRole();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [resubmitting, setResubmitting] = useState(false);
  const [editorText, setEditorText] = useState("");

  const loadData = async (resetText = false) => {
    try {
      const res = await getSubmissionDetail(id);
      setData(res);
      if (resetText && res.versions?.length > 0) setEditorText(res.versions[0].body);
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };
  
  useEffect(() => { loadData(true); }, [id]);

  const handleDecision = async (findingId, action, reason, edited_text) => {
    try {
      await recordDecision(findingId, { action, reason, edited_text });
      await loadData(false);
      return true;
    } catch (err) {
      alert(err.message);
      return false;
    }
  };

  const handleResubmit = async () => {
    setResubmitting(true);
    try { await resubmitPost(id, editorText); await loadData(true); } catch (err) { alert(err.message); } finally { setResubmitting(false); }
  };

  const handleAcceptFix = async (finding, fixText) => {
    // Only apply the fix if the flagged text is still in the editor.
    if (!canApplyFix(editorText, finding.excerpt)) {
      alert('The flagged text has changed since the last analysis. Click "Save Edits & Re-Analyze" first, then apply the fix.');
      return;
    }
    // Ask the server first; change the editor only if it accepted the decision.
    const ok = await handleDecision(finding.id, 'accept');
    if (ok) setEditorText((prev) => applyFixToText(prev, finding.excerpt, fixText));
  };

  if (loading || !data) return <Skeleton rows={3} label="Loading analysis" />;
  const { submission, current_findings } = data;
  const isCreator = currentRole === 'Creator';
  const isVisual = submission.channel === 'visual_asset';

  return (
    <main>
      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
        <div style={{ display: 'grid', gap: '18px', alignContent: 'start' }}>
          <div className="glass pad hoverlift">
            <div className="row" style={{justifyContent: 'space-between', marginBottom: '16px'}}>
              <h3 style={{margin: 0}}>{submission.title}</h3>
              <span className={`chip ${submission.status === 'blocked' ? 'blocked' : submission.status === 'needs_review' ? 'review' : 'ready'}`}>{submission.status.replace('_', ' ')}</span>
            </div>
            <div className="row" style={{gap: '16px', marginBottom: '20px', fontSize: '13px', color: 'var(--text-2)'}}>
              <span style={{textTransform:'capitalize'}}>Channel: {submission.channel}</span> | <span style={{textTransform:'capitalize'}}>Audience: {submission.audience}</span> | <span>v{submission.current_version}</span>
            </div>
            <div className="field">
              <label>{isVisual ? 'Image record' : 'Content Editor'}</label>
              <textarea value={editorText} onChange={e => setEditorText(e.target.value)} readOnly={isVisual || !isCreator} style={{height: '280px'}} />
            </div>
            {isVisual && <p style={{fontSize: '13px', color: 'var(--text-2)'}}>To fix an image, upload the corrected file as a new submission.</p>}
            {!isVisual && isCreator && (
              <div className="row" style={{marginTop: '20px'}}>
                <button onClick={handleResubmit} disabled={resubmitting} className="btn primary" style={{width: '100%'}}>
                  {resubmitting ? "Re-analyzing..." : "Save Edits & Re-Analyze"}
                </button>
              </div>
            )}
            {!isCreator && <p style={{fontSize: '13px', color: 'var(--text-2)'}}>Read-only for {currentRole}s. Only the Creator can edit and re-analyze.</p>}
          </div>
        </div>

        <div style={{ display: 'grid', gap: '18px', alignContent: 'start' }}>
          <h3 style={{marginLeft: '10px'}}>Findings ({current_findings.length})</h3>
          {current_findings.length === 0 && (
             <div className="glass pad"><span className="chip ready">All clear! No violations found in this version.</span></div>
          )}
          {current_findings.map(f => (
            <article key={f.id} className="glass pad hoverlift">
              {f.needs_human && f.decision === 'pending' && <div className="chip review" style={{marginBottom: '10px', width: '100%', justifyContent: 'center'}}>Needs Human Verification</div>}
              <div className="row" style={{justifyContent: 'space-between', marginBottom: '12px'}}>
                <div className="row">
                  <span className={`chip ${f.severity === 'high' ? 'blocked' : f.severity === 'medium' ? 'review' : 'info'}`}>{f.severity}</span>
                  <span className="chip id">{f.rule_or_fact_id}</span>
                </div>
                {f.decision !== 'pending' && <span className="chip ready" style={{textTransform:'capitalize'}}>{f.decision}ed</span>}
              </div>
              <p style={{marginBottom: '12px', fontSize: '16px'}}>
                <mark className={f.severity === 'high' ? 's-blocked' : 's-review'}>"{f.excerpt}"</mark>
              </p>
              <p style={{marginBottom: '16px', fontSize: '14px', color: 'var(--text)'}}>{f.explanation}</p>
              
              {f.decision === 'pending' && isCreator && (
                <div style={{marginTop: '16px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '16px'}}>
                  <div className="label" style={{marginBottom: '10px'}}>{isVisual ? 'Suggested fixes (apply them, then upload the corrected image)' : 'Suggested Fixes'}</div>
                  <div style={{display: 'grid', gap: '10px'}}>
                    <button disabled={isVisual} onClick={() => handleAcceptFix(f, f.fix_1)} className="btn" style={{justifyContent: 'flex-start', textAlign:'left', height: 'auto', padding: '12px'}}>
                      <strong>Option 1:</strong> <span style={{marginLeft: '6px', fontWeight: 'normal', color: 'var(--text-2)'}}>{f.fix_1}</span>
                    </button>
                    <button disabled={isVisual} onClick={() => handleAcceptFix(f, f.fix_2)} className="btn" style={{justifyContent: 'flex-start', textAlign:'left', height: 'auto', padding: '12px'}}>
                      <strong>Option 2:</strong> <span style={{marginLeft: '6px', fontWeight: 'normal', color: 'var(--text-2)'}}>{f.fix_2}</span>
                    </button>
                    <div className="row" style={{marginTop: '6px'}}>
                       <button onClick={() => { const r = prompt("Reason for rejection?"); if(r) handleDecision(f.id, 'reject', r); }} className="btn warn" style={{width: '100%'}}>Reject Finding</button>
                    </div>
                  </div>
                </div>
              )}
            </article>
          ))}
        </div>
      </div>
    </main>
  );
}
