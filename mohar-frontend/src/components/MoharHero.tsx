import "../styles/mohar-hero.css"; // Next.js: import "../app/mohar-hero.css"

const Apple = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M16.37 12.63c0-2.2 1.8-3.26 1.88-3.31-1.03-1.5-2.62-1.71-3.19-1.73-1.36-.14-2.65.8-3.34.8-.69 0-1.75-.78-2.88-.76-1.48.02-2.85.86-3.61 2.19-1.54 2.67-.39 6.62 1.1 8.79.74 1.06 1.62 2.25 2.77 2.21 1.11-.04 1.53-.72 2.88-.72 1.34 0 1.72.72 2.89.7 1.2-.02 1.95-1.08 2.68-2.15.85-1.23 1.2-2.43 1.22-2.49-.03-.01-2.33-.9-2.4-3.53zM14.2 6.15c.61-.74 1.02-1.77.91-2.8-.88.04-1.95.59-2.58 1.33-.57.65-1.06 1.7-.93 2.7.98.08 1.99-.5 2.6-1.23z" />
  </svg>
);
const Win = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M3 5.5 10.5 4.5v7H3zM11.5 4.4 21 3v8.5h-9.5zM3 12.5h7.5v7L3 18.5zM11.5 12.5H21V21l-9.5-1.4z" />
  </svg>
);
const Search = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
    <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
  </svg>
);
const Icon = ({ d }: { d: string }) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d={d} />
  </svg>
);
const Diamond = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
    <defs><linearGradient id="mhd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#ffb347" /><stop offset="1" stopColor="#ff2f3a" /></linearGradient></defs>
    <path d="M12 2 22 12 12 22 2 12z" fill="url(#mhd)" />
  </svg>
);

const rows = [
  { d: "M12 3v12m0-12 4 4m-4-4-4 4M5 21h14", label: "Approve brand asset", arg: "queue/pending", key: "⌘ Enter" },
  { d: "M3 7h18M3 12h18M3 17h18", label: "Open approval queue", arg: "~/mohar/queue", key: "⌘ B" },
  { d: "M4 4h16v16H4z", label: "Open brand guidelines", arg: "guidelines.md", key: "⌘ O" },
  { d: "M12 2v4m0 12v4M2 12h4m12 0h4", label: "Run governance check", arg: "pnpm audit:brand", key: "⌘ K" },
];

export default function MoharHero() {
  return (
    <div className="mh-root">
      <div className="mh-aurora" aria-hidden="true">
        <div className="mh-blade b1" /><div className="mh-blade b2" />
        <div className="mh-blade b3" /><div className="mh-blade b4" />
        <div className="mh-grain" /><div className="mh-vignette" />
      </div>

      <nav className="mh-nav">
        <a className="mh-brand" href="/"><Diamond />Mohar</a>
        <div className="mh-links">
          <a href="#product">Product</a><a href="#docs">Docs</a><a href="#pricing">Pricing</a>
          <a href="#changelog">Changelog</a><a href="#blog">Blog</a>
        </div>
        <div className="mh-navr">
          <a className="mh-login" href="/login">Log in</a>
          <a className="mh-pill-btn" href="#download"><Apple />Download</a>
        </div>
      </nav>

      <section className="mh-hero">
        <div className="mh-eyebrow">v2.0 · now with an AI command bar</div>
        <h1 className="mh-h1">Brand governance, <span className="mh-accent">approved</span> in one keystroke.</h1>
        <p className="mh-sub">Mohar keeps every asset, queue and approval on-brand, so your team ships faster without breaking the rules.</p>
        <div className="mh-cta">
          <a className="mh-key" href="#mac"><Apple />Download for Mac</a>
          <a className="mh-key" href="#win"><Win />Download for Windows</a>
        </div>
        <div className="mh-caption mh-mono">brew install mohar · Install via homebrew or winget</div>
      </section>

      <div className="mh-cmd" role="img" aria-label="Command bar preview">
        <div className="mh-cmd-top">
          <Search />
          <div className="mh-cmd-q">approve brand<span className="mh-caret" /></div>
          <span className="mh-mode mh-mono">Command</span>
        </div>
        <div className="mh-rows">
          {rows.map((r, i) => (
            <div key={r.label} className={"mh-row" + (i === 0 ? " active" : "")}>
              <Icon d={r.d} />
              <span>{r.label}<span className="arg mh-mono">{r.arg}</span></span>
              <span className="mh-chip mh-mono">{r.key}</span>
            </div>
          ))}
        </div>
        <div className="mh-foot mh-mono"><span>↑↓ navigate · enter open · esc dismiss</span><span>Mohar</span></div>
      </div>

      <div className="mh-ghost-wrap"><a className="mh-ghost" href="#product">Learn more →</a></div>

      <div className="mh-badge">
        <div className="mh-ph">P</div>
        <div><b>Featured on Product Hunt</b><span>#1 Product of the Day</span></div>
      </div>
    </div>
  );
}
