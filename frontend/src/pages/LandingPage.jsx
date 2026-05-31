import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Radio, Wifi, ShieldAlert, Navigation } from 'lucide-react';

export default function LandingPage() {
  const [utcTime, setUtcTime] = useState(new Date().toUTCString());

  // Update clock every second
  useEffect(() => {
    document.title = "RoadSoS — AI-Powered Emergency Assistance";
    const timer = setInterval(() => {
      const d = new Date();
      // Format as UTC HH:MM:SS
      const hh = String(d.getUTCHours()).padStart(2, '0');
      const mm = String(d.getUTCMinutes()).padStart(2, '0');
      const ss = String(d.getUTCSeconds()).padStart(2, '0');
      setUtcTime(`UTC ${hh}:${mm}:${ss}`);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="w-full min-h-screen flex flex-col md:flex-row bg-black text-white overflow-x-hidden">
      
      {/* Left Panel: Content (centered) */}
      <div className="w-full md:w-1/2 flex flex-col justify-between p-8 md:p-16 min-h-[50vh] md:min-h-screen z-10 bg-black">
        
        {/* Top Wordmark */}
        <div className="flex items-center">
          <span className="font-space font-bold text-2xl tracking-[0.2em] text-primary">
            ROADSOS
          </span>
        </div>

        {/* Center content */}
        <div className="my-auto py-12 flex flex-col items-start max-w-lg">
          <h1 className="font-bebas text-7xl md:text-8xl leading-none text-left tracking-wider m-0 mb-4 select-none">
            EVERY SECOND <br />
            <span className="text-primary drop-shadow-[0_0_12px_rgba(232,160,32,0.2)]">COUNTS.</span>
          </h1>

          <p className="font-body text-xs md:text-sm text-textSecondary tracking-[0.15em] leading-relaxed uppercase mb-8">
            AI-powered emergency assistance for mission-critical logistics and civilian safety.
          </p>

          <Link 
            to="/dashboard"
            className="group relative inline-flex items-center justify-center px-10 h-14 bg-primary text-black font-bebas text-xl tracking-wider rounded-pill transition-all duration-300 hover:bg-primary/90 hover:scale-[1.02] shadow-[0_0_15px_rgba(232,160,32,0.3)] hover:shadow-[0_0_25px_rgba(232,160,32,0.6)]"
          >
            OPEN DASHBOARD →
          </Link>
        </div>

        {/* Stats Row */}
        <div className="flex flex-wrap gap-3 font-mono text-[10px] tracking-wider text-textSecondary">
          <div className="glass-panel px-3 py-1.5 rounded-pill flex items-center gap-2 border border-white/5 bg-white/2 hover:border-primary/20 transition-all">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            2.3s response
          </div>
          <div className="glass-panel px-3 py-1.5 rounded-pill flex items-center gap-2 border border-white/5 bg-white/2 hover:border-info/20 transition-all">
            <span className="w-1.5 h-1.5 rounded-full bg-info" />
            50km radius
          </div>
          <div className="glass-panel px-3 py-1.5 rounded-pill flex items-center gap-2 border border-white/5 bg-white/2 hover:border-safe/20 transition-all">
            <span className="w-1.5 h-1.5 rounded-full bg-safe animate-pulse" />
            Works offline
          </div>
        </div>
      </div>

      {/* Right Panel: Map with CSS overlays */}
      <div className="w-full md:w-1/2 relative min-h-[50vh] md:min-h-screen bg-neutral-950 overflow-hidden border-t md:border-t-0 md:border-l border-white/10">
        
        {/* Background Satellite Image */}
        <img 
          src="/india_satellite_night.png" 
          alt="Satellite night map of India grid network" 
          className="absolute inset-0 w-full h-full object-cover opacity-60 mix-blend-screen scale-105 pointer-events-none select-none transition-transform duration-[20s] ease-out hover:scale-100"
        />

        {/* Ambient Dark Overlay Gradients */}
        <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-black/30 pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-r from-black via-transparent to-transparent pointer-events-none" />

        {/* Top-Right HUD Connectivity Card */}
        <div className="absolute top-6 right-6 z-10 glass-panel p-3 rounded-[8px] flex items-center gap-3 border border-white/10 hover:border-primary/40 transition-colors shadow-lg">
          <Wifi className="w-5 h-5 text-primary animate-pulse" />
          <div className="text-left font-mono">
            <div className="text-[9px] text-textTertiary leading-none tracking-widest uppercase">
              SYSTEM CONNECTIVITY
            </div>
            <div className="text-xs text-white font-bold leading-tight mt-0.5">
              SAT-LNK: ACTIVE (99.9%)
            </div>
          </div>
        </div>

        {/* Faint crosshairs at Mumbai & Delhi */}
        {/* Delhi Crosshair (top center-ish) */}
        <div className="absolute top-[32%] left-[45%] translate-x-[-50%] translate-y-[-50%] flex items-center justify-center pointer-events-none">
          <div className="w-6 h-6 border border-primary/20 rounded-full flex items-center justify-center">
            <span className="font-mono text-primary/45 text-[8px]">+</span>
          </div>
          <span className="absolute mt-8 font-mono text-[7px] text-textTertiary tracking-widest">
            DEL_GRID_28.6
          </span>
        </div>

        {/* Mumbai Crosshair (lower left-ish) */}
        <div className="absolute top-[62%] left-[32%] translate-x-[-50%] translate-y-[-50%] flex items-center justify-center pointer-events-none">
          <div className="w-6 h-6 border border-primary/20 rounded-full flex items-center justify-center">
            <span className="font-mono text-primary/45 text-[8px]">+</span>
          </div>
          <span className="absolute mt-8 font-mono text-[7px] text-textTertiary tracking-widest">
            MUM_GRID_19.0
          </span>
        </div>

        {/* Subtle grid stable mono label */}
        <div className="absolute top-[45%] right-[22%] font-mono text-[9px] text-textTertiary tracking-[0.2em] pointer-events-none select-none">
          NE_GRID_STABLE
        </div>

        {/* Bottom-Right Live Status Card */}
        <div className="absolute bottom-6 right-6 z-10 w-[300px] glass-panel p-4 rounded-[8px] border border-white/10 hover:border-danger/30 transition-all shadow-xl flex flex-col gap-3">
          
          <div className="flex items-center justify-between border-b border-white/5 pb-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-danger animate-pulse shadow-[0_0_8px_#E63946]" />
              <span className="font-mono text-[10px] text-danger tracking-wider uppercase font-bold">
                LIVE STATUS
              </span>
            </div>
            <span className="font-mono text-[9px] text-textSecondary">
              {utcTime}
            </span>
          </div>

          <div className="font-bebas text-xl text-white tracking-wide">
            3 ACTIVE EMERGENCIES
          </div>

          <div className="flex flex-col gap-1.5 font-mono text-[10px] text-left">
            <div className="flex items-center justify-between border-b border-white/5 pb-1">
              <span className="text-textSecondary">ZONE A - MUMBAI:</span>
              <span className="text-primary font-bold">DISPATCHED</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-textSecondary">ZONE D - DELHI:</span>
              <span className="text-danger font-bold animate-pulse">CRITICAL</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
