import React from 'react';
import { useSosStore } from '../store/useSosStore';
import { Info, CheckCircle2, ShieldAlert, X } from 'lucide-react';

export default function Toast() {
  const { toast, clearToast } = useSosStore();

  if (!toast) return null;

  let borderColor = 'border-primary/50';
  let glowColor = 'shadow-[0_0_12px_rgba(232,160,32,0.2)]';
  let Icon = Info;
  let iconColor = 'text-primary';

  if (toast.type === 'error') {
    borderColor = 'border-danger/50';
    glowColor = 'shadow-[0_0_12px_rgba(230,57,70,0.25)]';
    Icon = ShieldAlert;
    iconColor = 'text-danger';
  } else if (toast.type === 'success') {
    borderColor = 'border-safe/50';
    glowColor = 'shadow-[0_0_12px_rgba(46,204,113,0.2)]';
    Icon = CheckCircle2;
    iconColor = 'text-safe';
  }

  return (
    <div className="fixed top-6 left-1/2 transform -translate-x-1/2 z-[9999] w-full max-w-[420px] px-4 animate-in fade-in slide-in-from-top-4 duration-300 pointer-events-none">
      <div 
        className={`w-full bg-black/95 backdrop-blur-md border ${borderColor} rounded-[8px] p-3.5 flex items-center justify-between gap-3 ${glowColor} pointer-events-auto`}
        role="alert"
      >
        <div className="flex items-center gap-3 overflow-hidden text-left">
          <Icon className={`w-5 h-5 flex-shrink-0 ${iconColor} animate-pulse`} />
          <span className="font-mono text-xs text-white leading-normal tracking-wide">
            {toast.message.toUpperCase()}
          </span>
        </div>

        <button 
          onClick={clearToast}
          className="text-textSecondary hover:text-white transition-colors flex-shrink-0"
          aria-label="Dismiss notification"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
