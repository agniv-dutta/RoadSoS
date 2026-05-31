import React, { useState, useEffect, useRef } from 'react';
import { useSosStore } from '../store/useSosStore';
import { api } from '../api/client';
import { X, Send, Share2, ShieldAlert } from 'lucide-react';
import { getLocation } from '../utils/geo';
import { saveSosLog } from '../utils/offlineCache';

export default function SosModal() {
  const {
    sosActive,
    setSosActive,
    userLocation,
    setUserLocation,
    setToast,
    sosPrefillLocation,
    countdown,
    setCountdown,
    completeSos,
    cancelSos,
  } = useSosStore();
  const [coords, setCoords] = useState(userLocation);
  const [googleMapsUrl, setGoogleMapsUrl] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isSent, setIsSent] = useState(false);
  const timerRef = useRef(null);

  // Keyboard shortcut listener Ctrl+Shift+S
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 's') {
        e.preventDefault();
        setSosActive(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setSosActive]);

  // Geolocation lookup when modal opens
  useEffect(() => {
    if (!sosActive) return;

    // Reset state
    setCountdown(5);
    setIsSent(false);
    setIsSending(false);

    if (sosPrefillLocation?.lat != null && sosPrefillLocation?.lng != null) {
      setCoords(sosPrefillLocation);
      setUserLocation(sosPrefillLocation.lat, sosPrefillLocation.lng);
      return;
    }

    getLocation()
      .then((location) => {
        setCoords(location);
        setUserLocation(location.lat, location.lng);
      })
      .catch(() => {
        // Keep store location when geolocation cannot refresh.
        setCoords(userLocation);
      });

    if (!navigator.geolocation) {
      setCoords(userLocation);
    }
  }, [sosActive, userLocation, setUserLocation, setCountdown, sosPrefillLocation]);

  // Update Google Maps URL whenever coords change
  useEffect(() => {
    setGoogleMapsUrl(`https://www.google.com/maps/search/?api=1&query=${coords.lat},${coords.lng}`);
  }, [coords]);

  // Countdown timer logic
  useEffect(() => {
    if (!sosActive || isSent) return;

    if (countdown > 0) {
      timerRef.current = setTimeout(() => {
        setCountdown((prev) => prev - 1);
      }, 1000);
    } else {
      // Auto-trigger SOS when reaching 0
      triggerSos();
    }

    return () => clearTimeout(timerRef.current);
  }, [countdown, sosActive, isSent]);

  const triggerSos = async () => {
    if (isSending || isSent) return;
    setIsSending(true);
    try {
      const data = await api.sendSos(coords.lat, coords.lng, null);
      completeSos({ smsSent: data.sms_sent, sosSessionId: data.sos_id ? String(data.sos_id) : null });
      setIsSent(true);
      setToast('SOS Alert Sent Successfully!', 'success');
      console.log('SOS response:', data);
    } catch {
      saveSosLog({ latitude: coords.lat, longitude: coords.lng, phone: null });
      completeSos({ smsSent: false, sosSessionId: null });
      setToast('SOS queued offline and will sync when internet returns', 'error');
      setIsSent(true); // Treat as completed fallback
    } finally {
      setIsSending(false);
    }
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(googleMapsUrl);
    setToast('Google Maps SOS URL copied to clipboard!', 'success');
  };

  const getWhatsappUrl = () => {
    const text = `EMERGENCY ALERT! Active coordinates: ${coords.lat.toFixed(4)}° N, ${coords.lng.toFixed(4)}° E. Live Location: ${googleMapsUrl}`;
    return `https://wa.me/?text=${encodeURIComponent(text)}`;
  };

  if (!sosActive) return null;

  // SVG parameters for countdown ring
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (countdown / 5) * circumference;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4">
      {/* Modal Card */}
      <div 
        className="relative w-full max-w-[480px] bg-black border-2 border-danger rounded-[12px] shadow-[0_0_24px_rgba(230,57,70,0.4)] overflow-hidden flex flex-col"
        role="dialog"
        aria-modal="true"
      >
        {/* Top Danger Bar */}
        <div className="bg-danger px-4 py-3 flex items-center justify-between text-white">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 animate-pulse text-white" />
            <span className="font-bebas text-lg tracking-wider">EMERGENCY ALERT TRIGGERED</span>
          </div>
          <button 
            onClick={cancelSos}
            className="text-white/80 hover:text-white transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 flex flex-col items-center gap-5 text-center">
          {/* Countdown Ring */}
          <div className="relative w-[120px] h-[120px] flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="60"
                cy="60"
                r={radius}
                className="stroke-neutral-900 fill-none"
                strokeWidth="6"
              />
              <circle
                cx="60"
                cy="60"
                r={radius}
                className="stroke-primary fill-none transition-all duration-1000 ease-linear"
                strokeWidth="6"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
              />
            </svg>
            <span className="absolute font-bebas text-white text-6xl">
              {String(countdown).padStart(2, '0')}
            </span>
          </div>

          <div className="font-mono text-primary text-xs tracking-widest uppercase">
            {isSent ? "SOS ALERT DISPATCHED" : "INITIATING AUTOMATIC SOS"}
          </div>

          {/* Coordinates Info */}
          <div className="w-full bg-white/5 border border-white/10 rounded-[8px] p-3 text-left">
            <div className="font-mono text-[10px] text-primary tracking-wider uppercase mb-1">
              CURRENT COORDINATES
            </div>
            <div className="font-mono text-white text-sm">
              {coords.lat.toFixed(4)}° N, {coords.lng.toFixed(4)}° E
            </div>
          </div>

          {/* Location Link Share */}
          <div className="w-full bg-white/5 border border-white/10 rounded-[8px] p-3 text-left flex items-center justify-between">
            <div>
              <div className="font-mono text-[10px] text-primary tracking-wider uppercase mb-1">
                LIVE LOCATION LINK
              </div>
              <div className="font-body text-white/70 text-xs truncate max-w-[280px]">
                {googleMapsUrl}
              </div>
            </div>
            <button 
              onClick={handleCopyLink}
              className="p-2 hover:bg-white/10 rounded-full transition-colors text-primary hover:text-white"
              title="Copy location link"
            >
              <Share2 className="w-4 h-4" />
            </button>
          </div>

          {/* Action Buttons */}
          <div className="w-full flex flex-col gap-3 mt-2">
            <button
              onClick={triggerSos}
              disabled={isSending || isSent}
              className={`w-full py-3 bg-danger hover:bg-danger/90 text-white font-bebas text-lg tracking-wider rounded-pill transition-colors flex items-center justify-center gap-2 shadow-[0_0_12px_rgba(230,57,70,0.2)]`}
            >
              <Send className="w-4 h-4" />
              {isSending ? "SENDING..." : isSent ? "SOS SENT ✔" : "▶ SEND SOS SMS"}
            </button>

            <a
              href={getWhatsappUrl()}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => useSosStore.getState().setToast("Sharing via WhatsApp", "success")}
              className="w-full py-3 bg-safe hover:bg-safe/90 text-white font-bebas text-lg tracking-wider rounded-pill transition-colors flex items-center justify-center gap-2"
            >
              <Share2 className="w-4 h-4" />
              ⟲ SHARE VIA WHATSAPP
            </a>

            <button
              onClick={() => {
                cancelSos();
                setToast('SOS Alert Cancelled', 'info');
              }}
              className="w-full py-2 bg-transparent hover:bg-white/5 border border-white/20 text-neutral-400 hover:text-white text-xs font-body tracking-wider rounded-pill transition-colors"
            >
              CANCEL SOS
            </button>
          </div>
        </div>

        {/* Footer Secured */}
        <div className="border-t border-white/10 px-4 py-2 bg-black flex items-center justify-center gap-2">
          <span className="w-2 h-2 rounded-full bg-safe animate-pulse" />
          <span className="font-mono text-[9px] text-neutral-400 tracking-wider">SECURE UPLINK - ACTIVE</span>
        </div>
      </div>
    </div>
  );
}
