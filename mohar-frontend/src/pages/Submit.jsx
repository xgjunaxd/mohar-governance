import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { submitPost } from '../services/api';

const sanitizeInput = (str) => str.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '').replace(/[<>]/g, '');

export default function Submit() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState({ title: '', channel: 'social', audience: 'general', text: '', creator: 'Creator User' });

  const handleSample = () => setFormData({ ...formData, title: 'Diwali Campaign Draft', text: 'Hey bro! Astra Pay users can enjoy the "Diwali Dhamaka" cashback offer today. Want free money? Get guaranteed returns of 12% p.a. on your savings. Valid till Nov 30.' });

  const handleSubmit = async (e) => {
    e.preventDefault();
    const cleanTitle = sanitizeInput(formData.title.trim());
    const cleanText = sanitizeInput(formData.text.trim());
    if (cleanText.length < 10) { setError("Content draft must be at least 10 characters."); return; }
    if (cleanText.length > 2500) { setError("Content draft exceeds maximum safe limit of 2,500 characters."); return; }

    setLoading(true); setError(null);
    try {
      const res = await submitPost({ ...formData, title: cleanTitle, text: cleanText });
      navigate(`/findings/${res.submission_id}`);
    } catch (err) { setError(err?.response?.data?.detail || "Failed to reach server. Please check rate limits or backend status."); }
    finally { setLoading(false); }
  };

  return (
    <main>
      <div className="glass hero sheen hoverlift">
        <div className="row" style={{justifyContent: 'space-between', alignItems: 'center'}}>
          <div style={{flex: 1}}>
            <h1 style={{margin: '0 0 8px 0'}}>Submit Content</h1>
            <p style={{margin: 0}}>Run a brand compliance check before publishing.</p>
          </div>
          <button onClick={handleSample} type="button" className="btn">Try sample content</button>
        </div>
      </div>

      {error && <div className="glass pad" style={{marginBottom: '18px', color: 'var(--blocked)'}}><strong>Security / Validation Alert:</strong> {error}</div>}
      
      <form onSubmit={handleSubmit} className="glass pad hoverlift">
        <div className="field">
          <label>Internal Title (Max 120 chars)</label>
          <input required maxLength={120} type="text" placeholder="e.g., October Newsletter" value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} />
        </div>
        
        <div className="grid" style={{marginBottom: '14px', gridTemplateColumns: '1fr 1fr'}}>
          <div className="field">
            <label>Channel</label>
            <select value={formData.channel} onChange={e => setFormData({...formData, channel: e.target.value})}>
              <option value="social">Social Media</option>
              <option value="email">Email</option>
              <option value="web_copy">Website Copy</option>
            </select>
          </div>
          <div className="field">
            <label>Audience</label>
            <select value={formData.audience} onChange={e => setFormData({...formData, audience: e.target.value})}>
              <option value="general">General Public</option>
              <option value="existing_customers">Existing Customers</option>
              <option value="investors">Investors</option>
            </select>
          </div>
        </div>
        
        <div className="field">
          <div className="row" style={{justifyContent: 'space-between'}}>
            <label>Content Draft</label>
            <span style={{fontSize: '12px', color: 'var(--text-2)'}}>{formData.text.length} / 2500 chars</span>
          </div>
          <textarea required maxLength={2500} rows="6" placeholder="Paste your content here..." value={formData.text} onChange={e => setFormData({...formData, text: e.target.value})}></textarea>
        </div>
        
        <div className="row" style={{marginTop: '20px'}}>
          <button type="submit" disabled={loading || !formData.text} className="btn primary" style={{width: '100%'}}>
            {loading ? "Analyzing against verified rule ledger..." : "Run Mohar Analysis"}
          </button>
        </div>
      </form>
    </main>
  );
}
