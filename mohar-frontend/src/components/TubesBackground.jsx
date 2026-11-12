// mohar-frontend/src/components/TubesBackground.jsx
import React, { useEffect, useRef, useState } from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export default function TubesBackground({ children, className }) {
  const canvasRef = useRef(null);
  const tubesRef = useRef(null);

  useEffect(() => {
    let mounted = true;

    const initTubes = async () => {
      if (!canvasRef.current) return;
      try {
        const module = await import('https://cdn.jsdelivr.net/npm/threejs-components@0.0.19/build/cursors/tubes1.min.js');
        const TubesCursor = module.default;

        if (!mounted) return;

        // STRICTLY WARM PALETTE (No purple/indigo)
        tubesRef.current = TubesCursor(canvasRef.current, {
          tubes: {
            colors: ["#ff2f3a", "#ff6b4a", "#ffb347"],
            lights: {
              intensity: 150,
              colors: ["#ff2f3a", "#ffb347", "#ff6b4a", "#ff2f3a"]
            }
          }
        });
      } catch (error) {
        console.error("Failed to load TubesCursor:", error);
      }
    };

    initTubes();
    return () => { mounted = false; };
  }, []);

  return (
    <div className={cn("relative w-full h-full min-h-[400px] overflow-hidden bg-[#07080a]", className)}>
      
      {/* Layer 1: CSS Aurora Light Blades (Drifting & Breathing) */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none mix-blend-screen opacity-60">
        <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] bg-[#ff2f3a] rounded-full blur-[120px] animate-pulse" style={{ animationDuration: '18s' }} />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[70%] bg-[#ffb347] rounded-full blur-[140px] animate-pulse" style={{ animationDuration: '22s', animationDelay: '2s' }} />
        <div className="absolute top-[20%] right-[20%] w-[40%] h-[40%] bg-[#ff6b4a] rounded-full blur-[100px] animate-pulse" style={{ animationDuration: '15s', animationDelay: '5s' }} />
      </div>

      {/* Layer 2: SVG feTurbulence Film Grain */}
      <div className="absolute inset-0 pointer-events-none opacity-20 mix-blend-overlay">
        <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
          <filter id="noiseFilter">
            <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" stitchTiles="stitch"/>
          </filter>
          <rect width="100%" height="100%" filter="url(#noiseFilter)"/>
        </svg>
      </div>

      {/* Layer 3: Interactive 3D Cursor Tubes */}
      <canvas 
        ref={canvasRef} 
        className="absolute inset-0 w-full h-full block mix-blend-screen opacity-80"
        style={{ touchAction: 'none' }}
      />
      
      {/* Radial Vignette to darken edges */}
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,transparent_0%,#07080a_100%)] opacity-80" />

      {/* Content Overlay */}
      <div className="relative z-10 w-full h-full pointer-events-none">
        {children}
      </div>
    </div>
  );
}