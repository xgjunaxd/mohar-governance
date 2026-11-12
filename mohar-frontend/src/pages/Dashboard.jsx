// mohar-frontend/src/pages/Dashboard.jsx
import React from 'react';
import { Link } from 'react-router-dom';
import { Search, ChevronRight, Terminal, CheckCircle2, ShieldAlert, Cpu } from 'lucide-react';
import TubesBackground from '../components/TubesBackground';

export default function Dashboard() {
  return (
    <div className="w-full h-screen font-sans text-slate-100 bg-[#07080a] overflow-hidden selection:bg-[#ff6b4a]/30">
      <TubesBackground>
        
        {/* FLOATING PILL NAV */}
        <div className="pointer-events-auto fixed top-6 left-1/2 -translate-x-1/2 z-50 flex items-center justify-between w-[90%] max-w-4xl bg-[#07080a]/60 backdrop-blur-xl border border-white/10 rounded-full px-4 py-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.1),0_8px_32px_rgba(0,0,0,0.4)]">
          <div className="flex items-center gap-2 pl-2">
            <div className="w-4 h-4 rotate-45 bg-gradient-to-br from-[#ffb347] to-[#ff2f3a] rounded-sm" />
            <span className="font-semibold text-sm text-white tracking-tight">MOHAR</span>
          </div>
          
          <div className="hidden md:flex items-center gap-6 text-[13px] font-medium text-[#9c9c9d]">
            <Link to="/submit" className="hover:text-white transition-colors">Pipeline</Link>
            <Link to="/queue" className="hover:text-white transition-colors">Review Queue</Link>
            <span className="hover:text-white transition-colors cursor-pointer">Docs</span>
            <span className="hover:text-white transition-colors cursor-pointer">Changelog</span>
          </div>

          <div className="flex items-center gap-4">
            <Link to="/login" className="text-[13px] font-medium text-[#9c9c9d] hover:text-white transition-colors">Log in</Link>
            <Link to="/submit" className="text-[13px] font-medium bg-[#e6e6e6] text-[#2f3031] px-3 py-1.5 rounded-full hover:bg-white transition-colors flex items-center gap-1.5">
              Launch App
            </Link>
          </div>
        </div>

        {/* HERO CONTENT */}
        <div className="relative z-10 flex flex-col items-center justify-center w-full h-full pt-16 px-4">
          
          <div className="pointer-events-auto flex flex-col items-center text-center max-w-3xl">
            {/* Eyebrow */}
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/10 bg-white/5 text-[#9c9c9d] text-xs font-medium mb-6 backdrop-blur-md">
              <span className="w-1.5 h-1.5 rounded-full bg-[#ff6b4a] animate-pulse" />
              v2.0 — Now with an AI command bar
            </span>

            {/* Headline */}
            <h1 className="text-4xl md:text-[64px] font-semibold leading-[1.1] text-white tracking-tight mb-5 !text-[64px]">
              Everything you build, <br />
              <span className="bg-gradient-to-r from-[#ffb347] via-[#ff6b4a] to-[#ff2f3a] bg-clip-text text-transparent">
                strictly compliant.
              </span>
            </h1>

            {/* Subtitle */}
            <p className="text-lg text-[#9c9c9d] max-w-[640px] leading-relaxed mb-10 tracking-[0.2px]">
              Mohar is your AI-powered governance pipeline. Verify facts, enforce brand safety, and run automated compliance checks with one keystroke.
            </p>

            {/* TACTILE KEYCAP BUTTONS */}
            <div className="flex flex-col sm:flex-row items-center gap-4 mb-4">
              <Link to="/submit" className="group relative bg-[#e6e6e6] text-[#2f3031] font-medium text-sm px-5 py-3 rounded-lg flex items-center gap-2 shadow-[0_0_0_2px_#000,0_0_14px_rgba(255,255,255,0.15),inset_0_1px_0_rgba(255,255,255,1),inset_0_-2px_0_rgba(0,0,0,0.15)] active:translate-y-[1px] active:shadow-[0_0_0_2px_#000,0_0_8px_rgba(255,255,255,0.1),inset_0_1px_0_rgba(255,255,255,0.5),inset_0_-1px_0_rgba(0,0,0,0.1)] transition-all">
                <Terminal className="w-4 h-4 opacity-70" />
                Launch Web Workspace
              </Link>
              <button className="group relative bg-[#e6e6e6] text-[#2f3031] font-medium text-sm px-5 py-3 rounded-lg flex items-center gap-2 shadow-[0_0_0_2px_#000,0_0_14px_rgba(255,255,255,0.15),inset_0_1px_0_rgba(255,255,255,1),inset_0_-2px_0_rgba(0,0,0,0.15)] active:translate-y-[1px] active:shadow-[0_0_0_2px_#000,0_0_8px_rgba(255,255,255,0.1),inset_0_1px_0_rgba(255,255,255,0.5),inset_0_-1px_0_rgba(0,0,0,0.1)] transition-all">
                <svg className="w-4 h-4 opacity-70" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.379.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.161 22 16.418 22 12c0-5.523-4.477-10-10-10z"/></svg>
                Install CLI via GitHub
              </button>
            </div>
            
            <span className="font-mono text-[11px] text-[#9c9c9d] tracking-wide">
              npm install -g @mohar/cli — works on Mac, Windows, Linux
            </span>
          </div>

          {/* DARK-GLASS COMMAND BAR MOCKUP */}
          <div className="pointer-events-auto mt-12 w-full max-w-2xl bg-[#07080a]/80 backdrop-blur-2xl border border-white/10 rounded-2xl shadow-[0_24px_64px_-12px_rgba(255,47,58,0.15),inset_0_1px_0_rgba(255,255,255,0.05)] overflow-hidden">
            
            {/* Search Input Row */}
            <div className="flex items-center px-4 py-4 border-b border-white/5">
              <Search className="w-5 h-5 text-[#9c9c9d] mr-3" />
              <div className="flex-1 flex items-center">
                <span className="text-white text-base">run compliance check</span>
                <span className="w-0.5 h-5 bg-[#ff6b4a] ml-1 animate-pulse" />
              </div>
              <span className="text-[10px] uppercase tracking-wider font-semibold text-[#ffb347] bg-[#ffb347]/10 border border-[#ffb347]/20 px-2 py-1 rounded">
                Command
              </span>
            </div>

            {/* Results Rows */}
            <div className="p-2 space-y-1">
              
              {/* Active Row (Aurora Tinted) */}
              <div className="flex items-center justify-between px-3 py-2.5 bg-gradient-to-r from-[#ff2f3a]/15 to-transparent rounded-lg border border-[#ff2f3a]/20">
                <div className="flex items-center gap-3">
                  <ShieldAlert className="w-4 h-4 text-[#ff6b4a]" />
                  <span className="text-sm font-medium text-white">Scan project codebase</span>
                  <span className="font-mono text-xs text-[#ff6b4a]/70">src/pages/**/*.jsx</span>
                </div>
                <span className="font-mono text-[10px] text-white/50 bg-black/40 px-1.5 py-0.5 rounded border border-white/10">Cmd+Enter</span>
              </div>

              {/* Inactive Rows */}
              <div className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-white/5 transition-colors">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-4 h-4 text-[#9c9c9d]" />
                  <span className="text-sm font-medium text-[#9c9c9d]">Verify specific claim</span>
                  <span className="font-mono text-xs text-[#9c9c9d]/50">--fact "annual fee"</span>
                </div>
                <span className="font-mono text-[10px] text-[#9c9c9d]/50 bg-white/5 px-1.5 py-0.5 rounded border border-white/5">Cmd+F</span>
              </div>

              <div className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-white/5 transition-colors">
                <div className="flex items-center gap-3">
                  <Cpu className="w-4 h-4 text-[#9c9c9d]" />
                  <span className="text-sm font-medium text-[#9c9c9d]">Generate compliance report</span>
                  <span className="font-mono text-xs text-[#9c9c9d]/50">PDF Export</span>
                </div>
                <span className="font-mono text-[10px] text-[#9c9c9d]/50 bg-white/5 px-1.5 py-0.5 rounded border border-white/5">Cmd+P</span>
              </div>
            </div>

            {/* Footer Strip */}
            <div className="flex items-center justify-between px-4 py-2 bg-black/40 border-t border-white/5 text-[#9c9c9d]/60 font-mono text-[10px]">
              <div className="flex items-center gap-4">
                <span>↑↓ navigate</span>
                <span>↵ open</span>
                <span>esc dismiss</span>
              </div>
              <span className="font-sans font-semibold tracking-tight text-white/30">MOHAR V2</span>
            </div>
          </div>

          {/* Bottom Ghost Pill */}
          <Link to="/knowledge" className="pointer-events-auto mt-8 flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/10 text-xs text-[#9c9c9d] hover:text-white hover:bg-white/5 transition-colors">
            Learn more about the rules engine <ChevronRight className="w-3 h-3" />
          </Link>
          
        </div>

        {/* FLOATING BADGE (Bottom Right) */}
        <div className="pointer-events-auto absolute bottom-6 right-6 flex items-center gap-3 bg-[#07080a]/80 backdrop-blur-md border border-white/10 p-3 rounded-xl shadow-2xl">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[#ff6b4a] to-[#ffb347] flex items-center justify-center font-bold text-white shadow-inner">
            P
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-[#9c9c9d] font-semibold">Featured On</div>
            <div className="text-xs font-medium text-white">Product Hunt #1</div>
          </div>
        </div>

      </TubesBackground>
    </div>
  );
}