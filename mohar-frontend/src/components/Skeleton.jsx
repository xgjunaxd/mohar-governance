import React from 'react';

/* Loading placeholder shown while a page fetches its data. */
export default function Skeleton({ rows = 3, label = 'Loading', note }) {
  return (
    <main aria-busy="true">
      <span className="sr-only" role="status">{label}</span>
      <div className="glass hero sheen">
        <div className="skeleton sk-title" />
        <div className="skeleton sk-line" style={{ width: '55%' }} />
      </div>
      <div className="grid">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="glass pad">
            <div className="skeleton sk-line" style={{ width: '40%' }} />
            <div className="skeleton sk-line" />
            <div className="skeleton sk-line" style={{ width: '75%' }} />
          </div>
        ))}
      </div>
      {note && <p className="sk-note">{note}</p>}
    </main>
  );
}
