import React from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an exception:", error, errorInfo);
  }

  handleRestart = () => {
    window.location.href = '/dashboard';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="w-full min-h-screen bg-black text-white flex flex-col items-center justify-center p-8 font-mono">
          <div className="max-w-md w-full bg-neutral-950 border border-danger/40 p-6 rounded-[8px] shadow-[0_0_24px_rgba(230,57,70,0.2)] flex flex-col gap-4 text-center">
            
            <div className="flex justify-center text-danger animate-pulse">
              <AlertTriangle className="w-12 h-12" />
            </div>

            <h1 className="font-bebas text-3xl tracking-widest text-danger m-0">
              SYSTEM FAULT DETECTED
            </h1>

            <div className="text-[10px] text-textSecondary border border-white/10 p-3 rounded bg-white/2 text-left overflow-auto max-h-[150px] font-mono leading-relaxed">
              <span className="text-danger font-bold">ERROR_LOG:</span> {this.state.error?.toString() || "Unknown core exception"}
            </div>

            <p className="text-xs text-textSecondary leading-normal">
              An unexpected failure has halted the mission dashboard execution loop. Triage operations can be recovered.
            </p>

            <button
              onClick={this.handleRestart}
              className="mt-2 w-full py-2.5 bg-primary text-black font-bebas text-base tracking-wider rounded-pill hover:bg-primary/90 transition-all flex items-center justify-center gap-2 font-bold"
            >
              <RotateCcw className="w-4 h-4" />
              REBOOT COCKPIT
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
