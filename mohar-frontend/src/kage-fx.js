// Kage-style atmosphere + micro-interactions.
// Pure visual layer: it never touches app state, routes, or API calls.
// Everything is wrapped so that if anything fails, the app still works normally.
(function kageFx() {
  try {
    const root = document.documentElement;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    root.classList.add('kage-js');

    /* ---------- 1. Chapter label per page ---------- */
    const chapters = [
      [/^\/$/, '01 — WORKSPACE · 工房'],
      [/^\/submit/, '02 — SUBMIT · 提出'],
      [/^\/findings/, '03 — FINDINGS · 検証'],
      [/^\/queue/, '04 — APPROVALS · 承認'],
      [/^\/dashboard/, '05 — DASHBOARD · 概観'],
    ];
    let lastPath = null;
    function updateChapter() {
      const p = location.pathname;
      if (p === lastPath) return;
      lastPath = p;
      const hit = chapters.find(([re]) => re.test(p));
      root.style.setProperty('--chapter', '"' + (hit ? hit[1] : chapters[0][1]) + '"');
      window.scrollTo({ top: 0 });
    }

    /* ---------- 2. Scroll progress + moon parallax ---------- */
    const bar = document.createElement('div');
    bar.className = 'kage-progress';
    document.body.appendChild(bar);
    let ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const y = window.scrollY;
        const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
        root.style.setProperty('--sy', y.toFixed(0));
        bar.style.setProperty('--p', Math.min(1, y / max).toFixed(3));
        ticking = false;
      });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    onScroll();

    /* ---------- 3. Scroll reveal for cards and section titles ---------- */
    const io = 'IntersectionObserver' in window
      ? new IntersectionObserver((entries) => {
          entries.forEach((e) => {
            if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
          });
        }, { threshold: 0.06, rootMargin: '0px 0px -4% 0px' })
      : null;
    function scan() {
      document.querySelectorAll('main .glass:not([data-k]), main .sec:not([data-k])').forEach((el, i) => {
        el.dataset.k = '1';
        if (!io) { el.classList.add('in'); return; }
        el.style.transitionDelay = Math.min(i * 40, 240) + 'ms';
        io.observe(el);
      });
    }
    // React swaps content when you change pages or data loads: watch for it
    new MutationObserver(() => { updateChapter(); scan(); }).observe(
      document.getElementById('root'), { childList: true, subtree: true }
    );
    updateChapter(); scan();
    // safety net: never leave anything hidden
    setTimeout(() => document.querySelectorAll('main .glass:not(.in), main .sec:not(.in)').forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.top < window.innerHeight) el.classList.add('in');
    }), 1500);

    /* ---------- 4. Pointer glow on cards, magnetic primary buttons ---------- */
    if (fine && !reduce) {
      document.addEventListener('pointermove', (e) => {
        const card = e.target.closest && e.target.closest('.glass');
        if (card) {
          const r = card.getBoundingClientRect();
          card.style.setProperty('--gx', (e.clientX - r.left) + 'px');
          card.style.setProperty('--gy', (e.clientY - r.top) + 'px');
        }
        const btn = e.target.closest && e.target.closest('.btn.primary');
        if (btn) {
          const r = btn.getBoundingClientRect();
          const dx = (e.clientX - (r.left + r.width / 2)) / r.width;
          const dy = (e.clientY - (r.top + r.height / 2)) / r.height;
          btn.style.setProperty('--tx', (dx * 10).toFixed(1) + 'px');
          btn.style.setProperty('--ty', (dy * 8).toFixed(1) + 'px');
        }
      }, { passive: true });
      document.addEventListener('pointerout', (e) => {
        const btn = e.target.closest && e.target.closest('.btn.primary');
        if (btn) { btn.style.setProperty('--tx', '0px'); btn.style.setProperty('--ty', '0px'); }
      });

      /* ---------- 5. Cursor ring ---------- */
      const ring = document.createElement('div');
      ring.className = 'kage-cursor';
      document.body.appendChild(ring);
      let cx = -100, cy = -100, rx = -100, ry = -100;
      window.addEventListener('pointermove', (e) => {
        cx = e.clientX; cy = e.clientY;
        const hot = e.target.closest && e.target.closest('a,button,input,select,textarea,label');
        ring.classList.toggle('big', !!hot);
      }, { passive: true });
      (function follow() {
        rx += (cx - rx) * 0.2; ry += (cy - ry) * 0.2;
        ring.style.transform = 'translate3d(' + rx.toFixed(1) + 'px,' + ry.toFixed(1) + 'px,0)';
        requestAnimationFrame(follow);
      })();
    }

    /* ---------- 6. Falling maple leaves + embers (canvas) ---------- */
    const cv = document.getElementById('embers');
    if (cv && !reduce) {
      const ctx = cv.getContext('2d');
      let W = 0, H = 0, dpr = 1, running = true;
      const small = window.innerWidth < 820;
      const N = small ? 16 : 34;
      const parts = [];
      let mx = -999, my = -999;
      window.addEventListener('pointermove', (e) => { mx = e.clientX; my = e.clientY; }, { passive: true });
      function size() {
        dpr = Math.min(window.devicePixelRatio || 1, 1.5);
        W = cv.clientWidth; H = cv.clientHeight;
        cv.width = W * dpr; cv.height = H * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      }
      function make(first) {
        const leaf = Math.random() < 0.7;
        return {
          x: Math.random() * W, y: first ? Math.random() * H : -20,
          s: leaf ? 5 + Math.random() * 7 : 1 + Math.random() * 1.6,
          vy: 0.25 + Math.random() * 0.6, sw: Math.random() * Math.PI * 2, sws: 0.004 + Math.random() * 0.01,
          r: Math.random() * Math.PI * 2, vr: (Math.random() - 0.5) * 0.02,
          leaf, a: leaf ? 0.35 + Math.random() * 0.4 : 0.3 + Math.random() * 0.5,
          c: Math.random() < 0.6 ? '224,35,28' : '255,90,60',
        };
      }
      size();
      for (let i = 0; i < N; i++) parts.push(make(true));
      window.addEventListener('resize', size);
      document.addEventListener('visibilitychange', () => {
        running = !document.hidden; if (running) frame();
      });
      function frame() {
        if (!running) return;
        ctx.clearRect(0, 0, W, H);
        for (let i = 0; i < parts.length; i++) {
          const p = parts[i];
          p.sw += p.sws; p.r += p.vr;
          p.y += p.vy; p.x += Math.sin(p.sw) * 0.5 + 0.12;
          const dx = p.x - mx, dy = p.y - my, d2 = dx * dx + dy * dy;
          if (d2 < 9000) { const f = (1 - d2 / 9000) * 1.6; p.x += (dx / 90) * f; p.y += (dy / 90) * f; }
          if (p.y > H + 20 || p.x > W + 30) { parts[i] = make(false); parts[i].x = Math.random() * W; continue; }
          ctx.save();
          ctx.translate(p.x, p.y); ctx.rotate(p.r);
          ctx.fillStyle = 'rgba(' + p.c + ',' + p.a + ')';
          if (p.leaf) {
            ctx.beginPath();
            ctx.moveTo(0, -p.s);
            ctx.quadraticCurveTo(p.s * 0.9, -p.s * 0.2, 0, p.s);
            ctx.quadraticCurveTo(-p.s * 0.9, -p.s * 0.2, 0, -p.s);
            ctx.fill();
          } else {
            ctx.shadowColor = 'rgba(255,90,60,.9)'; ctx.shadowBlur = 6;
            ctx.beginPath(); ctx.arc(0, 0, p.s, 0, Math.PI * 2); ctx.fill();
          }
          ctx.restore();
        }
        requestAnimationFrame(frame);
      }
      frame();
    }
  } catch (err) {
    // Visual layer only: if anything goes wrong, show the plain app.
    document.documentElement.classList.remove('kage-js');
    console.warn('kage-fx disabled:', err);
  }
})();
