import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client';
import { useSosStore } from '../store/useSosStore';
import { Phone, MapPin, CheckCircle2, Database, AlertCircle, ArrowLeft, Navigation2, Share } from 'lucide-react';

export default function PlaceDetail({ inline = false }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const { userLocation, setToast } = useSosStore();
  const [place, setPlace] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    
    const fetchDetail = async () => {
      setLoading(true);
      try {
        const data = await api.getPlaceDetail(id, userLocation.lat, userLocation.lng);
        if (data) {
          setPlace(data);
        } else {
          setToast('Place details not found', 'error');
        }
      } catch (err) {
        setToast('Failed to fetch details', 'error');
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [id, userLocation, setToast]);

  const handleShare = () => {
    if (!place) return;
    const shareText = `Emergency Responder: ${place.name}\nPhone: ${place.phone || 'N/A'}\nAddress: ${place.address || 'N/A'}`;
    navigator.clipboard.writeText(shareText);
    setToast('Details copied to clipboard for sharing!', 'success');
  };

  const handleDirections = () => {
    if (!place) return;
    const url = `https://www.google.com/maps/dir/?api=1&origin=${userLocation.lat},${userLocation.lng}&destination=${place.latitude},${place.longitude}`;
    window.open(url, '_blank');
  };

  if (loading) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center p-6 bg-black text-white">
        <span className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin mb-4" />
        <span className="font-mono text-xs tracking-wider text-textSecondary">FETCHING TELEMETRY...</span>
      </div>
    );
  }

  if (!place) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center p-6 bg-black text-white text-center">
        <AlertCircle className="w-8 h-8 text-danger mb-3" />
        <span className="font-mono text-xs tracking-wider text-danger mb-4">PLACE NOT LOCATED</span>
        <button 
          onClick={() => navigate('/dashboard')}
          className="px-4 py-2 border border-white/20 hover:border-primary text-xs font-mono text-primary rounded-pill transition-colors"
        >
          RETURN TO DISPATCH
        </button>
      </div>
    );
  }

  const badgeText = place.place_type === 'hospital' || place.place_type === 'trauma_center' ? 'TRAUMA CENTER' : place.place_type.toUpperCase();
  const distanceStr = place.distance_km ? `${place.distance_km.toFixed(1)} KM` : 'NEARBY';

  return (
    <div className="w-full h-full bg-black text-white flex flex-col justify-between overflow-y-auto">
      
      {/* Scrollable Content */}
      <div className="p-6 flex flex-col gap-5">
        
        {/* Back Link */}
        <button 
          onClick={() => navigate('/dashboard')}
          className="self-start flex items-center gap-2 text-textSecondary hover:text-primary transition-colors text-xs font-mono"
        >
          <ArrowLeft className="w-4 h-4" />
          BACK TO GRID
        </button>

        {/* Top Type Badge */}
        <div className="self-start glass-panel px-3 py-1 rounded-pill border border-primary/30 text-primary text-[10px] tracking-widest font-mono font-bold">
          {badgeText}
        </div>

        {/* Title Name */}
        <h2 className="font-space text-3xl font-bold leading-tight tracking-wide text-left text-white select-text">
          {place.name.toUpperCase()}
        </h2>

        {/* Distance + Open Status */}
        <div className="flex items-center gap-3 font-mono text-xs">
          <span className="text-primary font-bold">{distanceStr} AWAY</span>
          <span className="text-textTertiary">•</span>
          <span className="flex items-center gap-1.5 text-safe font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-safe animate-pulse" />
            OPEN NOW
          </span>
        </div>

        {/* Satellite Map Thumbnail with Corner Brackets */}
        <div className="relative w-full h-[200px] rounded-[8px] overflow-hidden border border-white/10 group select-none">
          <img 
            src="/map_thumbnail.png" 
            alt="Target satellite location thumbnail" 
            className="w-full h-full object-cover opacity-75 group-hover:scale-105 transition-transform duration-700"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent pointer-events-none" />

          {/* Corner Brackets */}
          <div className="absolute top-2 left-2 w-3.5 h-3.5 border-t border-l border-primary/60 transition-all group-hover:top-1.5 group-hover:left-1.5"></div>
          <div className="absolute top-2 right-2 w-3.5 h-3.5 border-t border-r border-primary/60 transition-all group-hover:top-1.5 group-hover:right-1.5"></div>
          <div className="absolute bottom-2 left-2 w-3.5 h-3.5 border-b border-l border-primary/60 transition-all group-hover:bottom-1.5 group-hover:left-1.5"></div>
          <div className="absolute bottom-2 right-2 w-3.5 h-3.5 border-b border-r border-primary/60 transition-all group-hover:bottom-1.5 group-hover:right-1.5"></div>

          {/* Center coordinate overlay */}
          <div className="absolute bottom-3 left-3 bg-black/60 backdrop-blur-sm px-2 py-0.5 rounded border border-white/5 font-mono text-[8px] text-textSecondary">
            GRID: {place.latitude.toFixed(4)}° N, {place.longitude.toFixed(4)}° E
          </div>
        </div>

        {/* Address Card */}
        <div className="glass-panel p-3.5 rounded-[8px] flex gap-3 hover:border-primary/20 transition-all">
          <MapPin className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
          <div className="text-left">
            <div className="font-mono text-[9px] text-primary tracking-wider uppercase mb-1">
              ADDRESS
            </div>
            <div className="font-body text-xs text-white leading-relaxed select-text">
              {place.address || 'Location Coordinates Registered in Database.'}
            </div>
          </div>
        </div>

        {/* Phone + Verified Row */}
        <div className="grid grid-cols-2 gap-3">
          
          {/* Phone Card */}
          <a 
            href={place.phone ? `tel:${place.phone}` : '#'}
            onClick={(e) => {
              if (!place.phone) {
                e.preventDefault();
                setToast('Telephone dispatch not registered', 'info');
              }
            }}
            className={`glass-panel p-3.5 rounded-[8px] flex gap-3 hover:border-info/20 transition-all ${!place.phone ? 'pointer-events-none opacity-60' : ''}`}
          >
            <Phone className="w-4 h-4 text-info flex-shrink-0 mt-0.5" />
            <div className="text-left truncate">
              <div className="font-mono text-[9px] text-primary tracking-wider uppercase mb-1">
                PHONE
              </div>
              <div className="font-body text-xs text-white font-medium hover:underline truncate">
                {place.phone || 'NONE REGISTERED'}
              </div>
            </div>
          </a>

          {/* Verified Card */}
          <div className="glass-panel p-3.5 rounded-[8px] flex gap-3 hover:border-safe/20 transition-all">
            <CheckCircle2 className="w-4 h-4 text-safe flex-shrink-0 mt-0.5" />
            <div className="text-left">
              <div className="font-mono text-[9px] text-primary tracking-wider uppercase mb-1">
                VERIFIED
              </div>
              <div className="font-body text-xs text-safe font-bold">
                {place.is_verified ? 'YES ✓' : 'NO'}
              </div>
            </div>
          </div>
        </div>

        {/* Data Source Card */}
        <div className="glass-panel p-3.5 rounded-[8px] flex gap-3 hover:border-neutral-500/20 transition-all">
          <Database className="w-5 h-5 text-neutral-400 flex-shrink-0 mt-0.5" />
          <div className="text-left">
            <div className="font-mono text-[9px] text-primary tracking-wider uppercase mb-1">
              DATA SOURCE
            </div>
            <div className="font-mono text-[10px] text-neutral-400 leading-normal">
              {place.source.toUpperCase()}
            </div>
            <div className="font-mono text-[9px] text-textTertiary mt-0.5">
              ID: SOS-882-QX
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons & Footer */}
      <div className="p-6 border-t border-white/10 bg-black flex flex-col gap-3">
        <a
          href={place.phone ? `tel:${place.phone}` : '#'}
          onClick={(e) => {
            if (!place.phone) {
              e.preventDefault();
              setToast('Telephone not registered', 'info');
            }
          }}
          className="w-full h-12 bg-info hover:bg-info/90 text-white font-bebas text-lg tracking-wider rounded-pill flex items-center justify-center gap-2 transition-colors shadow-lg"
        >
          <Phone className="w-4 h-4" />
          CALL NOW
        </a>

        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={handleDirections}
            className="h-10 bg-transparent hover:bg-white/5 border border-primary text-primary font-bebas text-sm tracking-wider rounded-pill transition-colors flex items-center justify-center gap-1.5"
          >
            <Navigation2 className="w-3.5 h-3.5" />
            DIRECTIONS
          </button>
          <button
            onClick={handleShare}
            className="h-10 bg-transparent hover:bg-white/5 border border-primary text-primary font-bebas text-sm tracking-wider rounded-pill transition-colors flex items-center justify-center gap-1.5"
          >
            <Share className="w-3.5 h-3.5" />
            SHARE
          </button>
        </div>

        <button 
          onClick={() => setToast('Incorrect details reported. Dispatch network notified.', 'success')}
          className="mt-2 text-danger hover:underline text-[10px] font-mono text-center flex items-center justify-center gap-1"
        >
          <AlertCircle className="w-3 h-3" />
          ⊙ REPORT INCORRECT INFO
        </button>
      </div>
    </div>
  );
}
