import React from 'react';
import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <main>
      <div className="glass hero sheen">
        <h1>Page not found</h1>
        <p>The page you are looking for does not exist, or it moved. Nothing is broken on your side.</p>
        <div className="row" style={{ marginTop: '24px' }}>
          <Link to="/" className="btn primary">Back to the workspace</Link>
          <Link to="/dashboard" className="btn">Open the dashboard</Link>
        </div>
      </div>
    </main>
  );
}
