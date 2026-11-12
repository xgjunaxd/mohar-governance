import React, { useEffect, useState } from 'react';

/* Shows short pop-up messages (bottom right). Screen readers hear them (aria-live). */
export default function Toaster() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    const onToast = (e) => {
      const t = e.detail;
      setItems((cur) => [...cur.slice(-3), t]);
      setTimeout(() => setItems((cur) => cur.filter((x) => x.id !== t.id)), t.type === 'error' ? 6000 : 3500);
    };
    window.addEventListener('mohar:toast', onToast);
    return () => window.removeEventListener('mohar:toast', onToast);
  }, []);

  return (
    <div className="toasts" role="status" aria-live="polite">
      {items.map((t) => (
        <button key={t.id} type="button" className={`toast ${t.type}`} onClick={() => setItems((cur) => cur.filter((x) => x.id !== t.id))}>
          <span className="toast-dot" aria-hidden="true" />
          {t.text}
        </button>
      ))}
    </div>
  );
}
