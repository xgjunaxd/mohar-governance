import React, { useEffect, useRef } from 'react';

/* Interactive 3D "tubes" that follow the cursor (three.js, bundled with the app).
 *
 * - Loaded lazily, so the normal app loads fast and only the sign-in page pays for it.
 * - Strictly warm colours (crimson / coral / amber), clicking the background picks new warm colours.
 * - Skipped when the visitor prefers reduced motion, is on a phone or tablet, or has no WebGL.
 *   The CSS aurora behind it is always there, so nothing looks missing.
 */
const WARM = ['#ff2f3a', '#ff6b4a', '#ffb347'];
const WARM_LIGHTS = ['#ff2f3a', '#ffb347', '#ff6b4a', '#ff8a2e'];

function hslToHex(h, s, l) {
  s /= 100; l /= 100;
  const k = (n) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  const x = (v) => Math.round(255 * v).toString(16).padStart(2, '0');
  return `#${x(f(0))}${x(f(8))}${x(f(4))}`;
}
const warmHex = () => hslToHex(Math.random() * 42, 100, 55); // hue 0-42 = red to amber only

function webglAvailable() {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch {
    return false;
  }
}

export default function TubesLayer() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const touchLike = window.matchMedia('(pointer: coarse)').matches || window.innerWidth < 760;
    if (reduce || touchLike || !webglAvailable() || !canvasRef.current) return undefined;

    const canvas = canvasRef.current;
    let app = null;
    let cancelled = false;

    (async () => {
      try {
        const mod = await import('threejs-components/build/cursors/tubes1.min.js');
        if (cancelled) return;
        app = mod.default(canvas, {
          tubes: { colors: WARM, lights: { intensity: 150, colors: WARM_LIGHTS } },
        });
        canvas.classList.add('ready');
      } catch (err) {
        console.warn('Tubes background unavailable, using the aurora only.', err);
      }
    })();

    const recolour = () => {
      if (!app || !app.tubes) return;
      app.tubes.setColors([warmHex(), warmHex(), warmHex()]);
      app.tubes.setLightsColors([warmHex(), warmHex(), warmHex(), warmHex()]);
    };
    canvas.addEventListener('click', recolour);

    return () => {
      cancelled = true;
      canvas.removeEventListener('click', recolour);
      try { if (app && app.dispose) app.dispose(); } catch { /* already gone */ }
      app = null;
    };
  }, []);

  return <canvas ref={canvasRef} className="mh-tubes" aria-hidden="true" />;
}
