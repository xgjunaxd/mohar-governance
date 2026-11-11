import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { submitPost, submitVisual } from '../services/api';

const sanitizeInput = (str) => str.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '').replace(/[<>]/g, '');

export default function Submit() {
  const navigate = useNavigate();
  const [tab, setTab] = useState('text');
  const [loading, setLoading] = useState(false);
  const [img, setImg] = useState({ file: null, alt: '', title: '', preview: '' });
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
    } catch (err) { setError(err.message || "Failed to reach server. Please check rate limits or backend status."); }
    finally { setLoading(false); }
  };

  const pickImage = (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { setError('Image is too large (max 5 MB).'); return; }
    if (img.preview) URL.revokeObjectURL(img.preview);
    setError(null);
    setImg({ ...img, file, preview: URL.createObjectURL(file), title: img.title || file.name.replace(/\.[^.]+$/, '') });
  };

  const handleImageSubmit = async (e) => {
    e.preventDefault();
    if (!img.file) { setError('Please choose an image first.'); return; }
    setLoading(true); setError(null);
    try {
      const res = await submitVisual(img.file, sanitizeInput(img.alt.trim()), sanitizeInput(img.title.trim()));
      navigate(`/findings/${res.submission_id}`);
    } catch (err) { setError(err.message); }
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

      <div className="seg" role="group" aria-label="Content type" style={{ marginBottom: '18px', width: 'fit-content' }}>
        <button type="button" aria-pressed={tab === 'text'} onClick={() => { setTab('text'); setError(null); }}>Text post</button>
        <button type="button" aria-pressed={tab === 'image'} onClick={() => { setTab('image'); setError(null); }}>Image / poster</button>
      </div>

      {error && <div className="glass pad" style={{marginBottom: '18px', color: 'var(--blocked)'}}><strong>Security / Validation Alert:</strong> {error}</div>}
      
      {tab === 'text' && (
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
      )}

      {tab === 'image' && (
        <form onSubmit={handleImageSubmit} className="glass pad hoverlift">
          <div className="field">
            <label>Image or poster (PNG, JPEG or WebP, max 5 MB)</label>
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={pickImage} />
          </div>
          {img.preview && <img src={img.preview} alt="Preview of the selected upload" style={{ maxWidth: '100%', maxHeight: '260px', borderRadius: '12px', marginBottom: '16px' }} />}
          <div className="field">
            <label>Internal title</label>
            <input maxLength={120} type="text" placeholder="e.g., Diwali poster" value={img.title} onChange={(e) => setImg({ ...img, title: e.target.value })} />
          </div>
          <div className="field">
            <label>Alt text (describe the image for screen-reader users)</label>
            <textarea rows="3" maxLength={500} placeholder="e.g., AstraPay app showing a UPI payment confirmation screen" value={img.alt} onChange={(e) => setImg({ ...img, alt: e.target.value })}></textarea>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-2)' }}>Mohar checks alt text, text contrast (4.5:1) and brand colours. Contrast is estimated from the image's main colours.</p>
          <button type="submit" disabled={loading || !img.file} className="btn primary" style={{ width: '100%' }}>
            {loading ? 'Checking image...' : 'Run Visual Check'}
          </button>
        </form>
      )}
    </main>
  );
}
