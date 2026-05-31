import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { useSosStore } from '../store/useSosStore';
import { api } from '../api/client';
import { checkHealth } from '../api/index';
import PlaceDetail from './PlaceDetail';
import {
  Radio, Wifi, WifiOff, Bell, Settings, Search, MapPin,
  Flame, Shield, Truck, Cross, ChevronRight, Share, Navigation,
  CloudLightning, AlertCircle, Info, ShieldAlert, HeartHandshake,
  Activity, Users, FileText, ChevronDown, CheckCircle2,
  RefreshCw, Ambulance, Fuel, Zap, Clock, Database
} from 'lucide-react';
import { isDemoMode } from '../utils/demoData';

// ─── Dev-only log helper ─────────────────────────────────────────────────────
const devLog = (...args) => {
  if (import.meta.env.DEV) console.log(...args);
};

// ─── City lookup ─────────────────────────────────────────────────────────────
function getCityFromCoords(lat, lng) {
  if (lat >= 18 && lat <= 20) return 'MUMBAI';
  if (lat >= 28 && lat <= 29) return 'DELHI';
  return `${lat.toFixed(2)}°N`;
}

// ─── Constants ───────────────────────────────────────────────────────────────
const DISTRESS_KEYWORDS = [
  'accident', 'crash', 'help', 'injured', 'hurt', 'bleeding', 'fire',
  'trapped', 'emergency', 'ambulance', 'dying', 'dead', 'unconscious',
  'stuck', 'collision',
  'madad', 'bachao', 'chot', 'khoon', 'aag', 'phas',
  'sahajjo', 'raktopat', 'agun', 'fese',
];

const FILTER_TABS = ['all', 'hospital', 'police', 'ambulance', 'towing'];

const TYPE_CONFIG = {
  hospital:    { color: '#E63946', label: 'RESPONSIVE',  statusClass: 'text-danger',  Icon: HeartHandshake },
  trauma_center:{ color: '#E63946', label: 'RESPONSIVE', statusClass: 'text-danger',  Icon: HeartHandshake },
  police:      { color: '#3A86FF', label: 'ACTIVE DUTY', statusClass: 'text-info',    Icon: Shield },
  ambulance:   { color: '#2ECC71', label: 'AVAILABLE',   statusClass: 'text-safe',    Icon: Ambulance },
  towing:      { color: '#E8A020', label: 'ON ROUTE',    statusClass: 'text-primary', Icon: Truck },
  fuel:        { color: '#A0A0A0', label: 'OPEN',        statusClass: 'text-textSecondary', Icon: Fuel },
  fire_station:{ color: '#E63946', label: 'ON DUTY',     statusClass: 'text-danger',  Icon: Flame },
};

function getTypeConfig(place_type) {
  return TYPE_CONFIG[place_type] || { color: '#E8A020', label: 'AVAILABLE', statusClass: 'text-primary', Icon: Truck };
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function isEmergencyMessage(text) {
  const lower = String(text || '').toLowerCase();
  const wordCount = text.trim().split(/\s+/).length;
  const hasKeyword = DISTRESS_KEYWORDS.some(k => lower.includes(k));
  return wordCount >= 4 || hasKeyword;
}

function parseLocationSlot(slots) {
  const locationText = slots?.LOCATION || slots?.location || slots?.location_mention || null;
  if (!locationText || typeof locationText !== 'string') return null;
  const match = locationText.match(/(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)/);
  if (!match) return null;
  const lat = Number(match[1]);
  const lng = Number(match[2]);
  if (Number.isNaN(lat) || Number.isNaN(lng)) return null;
  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;
  return { lat, lng };
}

function getLastUpdatedMeta(lastSynced) {
  if (!lastSynced) {
    return { label: 'Updated unknown', toneClass: 'text-danger', warning: 'Data may be outdated.', staleLevel: 'very-stale' };
  }
  const now = Date.now();
  const syncedMs = new Date(lastSynced).getTime();
  const ageHours = Math.max(0, (now - syncedMs) / (1000 * 60 * 60));
  const ageMinutes = Math.max(0, Math.floor((now - syncedMs) / (1000 * 60)));
  let label = 'Updated just now';
  if (ageMinutes >= 60) label = `Updated ${Math.floor(ageMinutes / 60)}h ago`;
  else if (ageMinutes >= 1) label = `Updated ${ageMinutes}m ago`;
  if (ageHours > 72) return { label, toneClass: 'text-danger', warning: 'Data may be outdated.', staleLevel: 'very-stale' };
  if (ageHours > 24) return { label, toneClass: 'text-primary', warning: null, staleLevel: 'stale' };
  return { label, toneClass: 'text-textSecondary', warning: null, staleLevel: 'fresh' };
}

function confidenceTone(confidence) {
  if (confidence >= 0.85) return 'bg-safe';
  if (confidence >= 0.6) return 'bg-primary';
  return 'bg-danger';
}

// ─── Skeleton Card ────────────────────────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="glass-panel p-3.5 rounded-[8px] border border-white/5 flex flex-col gap-3 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-[8px] bg-white/10 flex-shrink-0" />
        <div className="flex flex-col gap-2 flex-1">
          <div className="h-3 w-3/4 rounded bg-white/10" />
          <div className="h-2 w-1/2 rounded bg-white/5" />
        </div>
        <div className="h-3 w-10 rounded bg-white/10" />
      </div>
      <div className="h-1.5 w-full rounded-full bg-white/10" />
    </div>
  );
}

// ─── Map helpers ─────────────────────────────────────────────────────────────
function MapController({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center) map.setView([center.lat, center.lng], zoom || map.getZoom());
  }, [center, zoom, map]);
  return null;
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────
export default function Dashboard() {
  const navigate = useNavigate();
  const { id } = useParams();
  const currentQuery = typeof window !== 'undefined' ? window.location.search : '';

  const {
    lat, lng,
    userLocation, setUserLocation,
    onlineStatus, setOnlineStatus,
    setSosActive, startSos,
    places, nearbyPlaces, setNearbyPlaces,
    selectedPlace, setSelectedPlace,
    setToast,
    fromCache, setFromCache,
    offlineIncidents, loadOfflineCache,
    sessionId, setTriageSessionId, setTriageResult, addTriageMessage,
    isLoading, setNearbyLoading,
  } = useSosStore();

  // Issues 1&2 — live lat/lng and city name from store
  const storeLat = lat ?? userLocation?.lat ?? 19.076;
  const storeLng = lng ?? userLocation?.lng ?? 72.8777;

  const [activeTab, setActiveTab] = useState('dispatch');
  const [activeFilter, setActiveFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchPlaceholder, setSearchPlaceholder] = useState('CMD: Search Dispatch Grid...');
  const [mapZoom, setMapZoom] = useState(13);
  const [isHoldingSos, setIsHoldingSos] = useState(false);
  const [triageResult, setLocalTriageResult] = useState(null);
  const [triageLoading, setTriageLoading] = useState(false);
  const [capExpanded, setCapExpanded] = useState(false);
  const [searchMode, setSearchMode] = useState('places');
  const [awaitingSlot, setAwaitingSlot] = useState(false);
  const [fetchError, setFetchError] = useState(false);
  const [telemetryData, setTelemetryData] = useState(null);
  const [telemetryLoading, setTelemetryLoading] = useState(false);
  const [cacheAge, setCacheAge] = useState(null);
  const [lastInference, setLastInference] = useState(null);
  const holdTimerRef = useRef(null);
  const demoMode = isDemoMode();

  // Issue 1 — city name, updated every 30 s
  const [cityName, setCityName] = useState(() => getCityFromCoords(storeLat, storeLng));
  useEffect(() => {
    setCityName(getCityFromCoords(storeLat, storeLng));
    const interval = setInterval(() => {
      const s = useSosStore.getState();
      const la = s.lat ?? s.userLocation?.lat ?? storeLat;
      const lo = s.lng ?? s.userLocation?.lng ?? storeLng;
      setCityName(getCityFromCoords(la, lo));
    }, 30000);
    return () => clearInterval(interval);
  }, [storeLat, storeLng]);

  // Issue 2 — real activeOps from store
  const activeOps = (places ?? nearbyPlaces ?? []).length;

  useEffect(() => {
    document.title = 'RoadSoS — Tactical Dashboard';
  }, []);

  // Fetch places
  const fetchPlaces = useCallback(async () => {
    if (!onlineStatus) { loadOfflineCache(); return; }
    setNearbyLoading(true);
    setFetchError(false);
    try {
      const data = await api.getNearby(storeLat, storeLng, 10);
      if (data && data.results) {
        setNearbyPlaces(data.results);
        setFromCache(Boolean(data.from_cache));
        // Compute cache age
        if (data.cache_timestamp) {
          const ageMins = Math.round((Date.now() - new Date(data.cache_timestamp).getTime()) / 60000);
          setCacheAge(ageMins);
        }
      }
    } catch {
      setFromCache(true);
      setFetchError(true);
    } finally {
      setNearbyLoading(false);
    }
  }, [onlineStatus, storeLat, storeLng, setNearbyPlaces, setFromCache, loadOfflineCache, setNearbyLoading]);

  useEffect(() => { fetchPlaces(); }, [userLocation, onlineStatus]);

  // Place detail routing
  useEffect(() => {
    if (id) {
      const place = (places ?? nearbyPlaces ?? []).find(p => p.id === parseInt(id));
      if (place) { setSelectedPlace(place); setMapZoom(14); }
    } else {
      setSelectedPlace(null);
      setMapZoom(13);
    }
  }, [id, places, nearbyPlaces, setSelectedPlace]);

  // Issue 4 — fetch telemetry when tab active
  useEffect(() => {
    if (activeTab !== 'telemetry' || !onlineStatus) return;
    setTelemetryLoading(true);
    checkHealth()
      .then(data => setTelemetryData(data))
      .catch(() => setTelemetryData(null))
      .finally(() => setTelemetryLoading(false));
  }, [activeTab, onlineStatus]);

  const handleShareLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          setUserLocation(latitude, longitude);
          setToast('Location synchronized successfully', 'success');
        },
        () => setToast('Unable to fetch current location. Check browser settings.', 'error')
      );
    } else {
      setToast('Geolocation is not supported by your browser.', 'error');
    }
  };

  const startHoldSos = () => {
    setIsHoldingSos(true);
    holdTimerRef.current = setTimeout(() => {
      setIsHoldingSos(false);
      setSosActive(true);
    }, 1500);
  };

  const endHoldSos = () => {
    setIsHoldingSos(false);
    if (holdTimerRef.current) clearTimeout(holdTimerRef.current);
  };

  const handleCommandSubmit = async () => {
    const text = searchQuery.trim();
    if (!text || !onlineStatus) return;

    if (isEmergencyMessage(text) || awaitingSlot) {
      setSearchMode('triage');
      setTriageLoading(true);
      const startMs = Date.now();
      try {
        const parsed = await api.parseTriageMessage(text, sessionId || null, null);
        const inferenceMs = Date.now() - startMs;
        const normalized = {
          intent: parsed.intent || 'unknown',
          triage: parsed.triage_result || parsed.triage || parsed.triage_level || 'P3',
          slots: parsed.filled_slots || parsed.slots || {},
          cap_alert: parsed.cap_alert || null,
          session_id: parsed.session_id || null,
          follow_up_question: parsed.follow_up_question || null,
          ready_to_dispatch: parsed.ready_to_dispatch || false,
        };

        setLocalTriageResult(normalized);
        setTriageResult(normalized);
        addTriageMessage({ role: 'user', text, timestamp: Date.now() });
        setLastInference({ ms: inferenceMs, intent: normalized.intent, triage: normalized.triage });

        if (normalized.session_id) setTriageSessionId(normalized.session_id);

        if (normalized.follow_up_question) {
          setSearchPlaceholder(normalized.follow_up_question);
          setAwaitingSlot(true);
        } else {
          setSearchPlaceholder('CMD: Search Dispatch Grid...');
          setAwaitingSlot(false);
        }

        const prefilledLocation = parseLocationSlot(normalized.slots);
        if (normalized.triage === 'P1') startSos(normalized.session_id || null, prefilledLocation);

        if (normalized.ready_to_dispatch) {
          setSearchPlaceholder('Ready for next emergency');
          setAwaitingSlot(false);
          try {
            const data = await api.getNearby(storeLat, storeLng, 10);
            if (data && data.results) setNearbyPlaces(data.results);
          } catch { /* silent */ }
          setTriageSessionId(null);
        }

        setSearchQuery('');
      } catch (error) {
        setToast(error.message || 'Failed to parse triage message', 'error');
      } finally {
        setTriageLoading(false);
      }
    } else {
      setSearchMode('places');
      setLocalTriageResult(null);
      try {
        const data = await api.getNearby(storeLat, storeLng, 10, text);
        if (data && data.results) {
          setNearbyPlaces(data.results);
          setFromCache(Boolean(data.from_cache));
        }
      } catch (error) {
        setToast(error.message || 'Place search failed', 'error');
      }
    }
  };

  // Issue 3 — extended filter logic for ambulance/towing
  const allPlaces = places ?? nearbyPlaces ?? [];
  const filteredPlaces = allPlaces.filter(place => {
    if (activeFilter === 'hospital') return place.place_type === 'hospital' || place.place_type === 'trauma_center';
    if (activeFilter === 'police') return place.place_type === 'police';
    if (activeFilter === 'ambulance') return place.place_type === 'ambulance';
    if (activeFilter === 'towing') return place.place_type === 'towing';
    if (searchMode === 'places' && searchQuery.trim() !== '') {
      return place.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (place.address && place.address.toLowerCase().includes(searchQuery.toLowerCase()));
    }
    return true;
  });

  // Map markers
  const getCustomMarkerIcon = (place) => {
    const cfg = getTypeConfig(place.place_type);
    const color = cfg.color;
    const text = place.place_type === 'hospital' || place.place_type === 'trauma_center' ? '+' :
      place.place_type === 'police' ? 'P' :
      place.place_type === 'ambulance' ? 'A' :
      place.place_type === 'fuel' ? 'F' : 'T';

    return L.divIcon({
      html: `<div style="width:32px;height:32px;border-radius:50%;background:#0a0a0a;border:1.5px solid rgba(255,255,255,0.2);display:flex;align-items:center;justify-content:center;box-shadow:0 0 8px ${color}50">
        <span style="color:${color};font-size:13px;font-weight:bold;font-family:monospace">${text}</span>
      </div>`,
      className: 'custom-marker',
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    });
  };

  const userIcon = L.divIcon({
    html: `<div class="pulsing-marker"></div>`,
    className: 'user-marker',
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });

  const hospitals = allPlaces.filter(p => p.place_type === 'hospital');
  const nearestHospital = hospitals.length > 0 ? hospitals[0] : null;

  // ─── Render helpers ──────────────────────────────────────────────────────────

  const renderDispatchTab = () => (
    <div className="w-full md:w-[380px] bg-black border-b md:border-b-0 md:border-r border-white/10 flex flex-col overflow-hidden z-10 flex-shrink-0">
      {/* Search */}
      <div className="p-4 border-b border-white/10 bg-neutral-950 flex flex-col gap-3">
        <div className="relative">
          <Search className="w-4 h-4 text-textTertiary absolute left-3 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              if (!e.target.value.trim()) {
                setSearchMode('places');
                setAwaitingSlot(false);
                setLocalTriageResult(null);
                setSearchPlaceholder('CMD: Search Dispatch Grid...');
                setTriageSessionId(null);
              }
            }}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleCommandSubmit(); } }}
            placeholder={searchPlaceholder}
            disabled={!onlineStatus}
            className={`w-full h-10 pl-9 pr-4 bg-white/3 border border-white/10 rounded-[8px] text-xs font-mono placeholder:text-textTertiary text-white focus:outline-none focus:border-primary focus:shadow-[0_0_8px_rgba(232,160,32,0.25)] transition-all ${!onlineStatus ? 'opacity-60 cursor-not-allowed' : ''}`}
          />
        </div>
        {triageLoading && <div className="text-[10px] font-mono text-primary tracking-wider animate-pulse">ANALYZING EMERGENCY MESSAGE...</div>}
        {searchMode === 'triage' && triageResult && renderTriageCard()}
      </div>

      {/* Panel Header */}
      <div className="px-4 py-3.5 flex items-center justify-between">
        {onlineStatus ? (
          <>
            <div className="flex items-center gap-1">
              <span className="font-bebas text-2xl tracking-wider text-primary">NEARBY</span>
              <span className="font-bebas text-2xl tracking-wider text-white">RESCUE</span>
            </div>
            <ChevronRight className="w-4 h-4 text-primary" />
          </>
        ) : (
          <>
            <span className="font-bebas text-2xl tracking-wider text-danger">CACHED INCIDENTS</span>
            <span className="glass-panel px-2.5 py-0.5 border border-primary/20 text-primary text-[8px] tracking-widest font-mono font-bold rounded-pill">● LOCAL CACHE</span>
          </>
        )}
      </div>

      {/* Issue 3 — extended filter tabs */}
      {onlineStatus && (
        <div className="px-4 pb-3 flex gap-1.5 border-b border-white/10 overflow-x-auto">
          {FILTER_TABS.map((filter) => (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              className={`px-3 py-1.5 rounded-pill font-mono text-[9px] uppercase tracking-wider border transition-all flex-shrink-0 ${
                activeFilter === filter
                  ? 'border-primary text-primary font-bold bg-primary/5'
                  : 'border-white/10 text-textSecondary hover:text-white'
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
      )}

      {/* List Content */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {onlineStatus ? renderOnlineList() : renderOfflineList()}
      </div>
    </div>
  );

  const renderOnlineList = () => {
    // Issue 7 — Loading skeletons
    if (isLoading) {
      return [0, 1, 2].map(i => <SkeletonCard key={i} />);
    }

    // Issue 6 — graceful empty / error state
    if (fetchError || filteredPlaces.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center gap-4 h-full text-center py-8">
          <div className="w-12 h-12 rounded-full bg-white/5 border border-white/10 flex items-center justify-center">
            <AlertCircle className="w-5 h-5 text-textTertiary" />
          </div>
          <div>
            <div className="font-bebas text-lg tracking-wider text-white">NO DISPATCH FOUND IN SECTOR</div>
            <div className="font-mono text-[10px] text-textSecondary mt-1 leading-relaxed">
              {fetchError
                ? 'Try increasing radius or check backend connection'
                : activeFilter !== 'all'
                  ? `No ${activeFilter} resources in range. Try the ALL tab.`
                  : 'Try increasing radius or check backend connection'}
            </div>
          </div>
          <button
            onClick={fetchPlaces}
            className="flex items-center gap-2 px-4 py-2 rounded-pill border border-primary/40 text-primary font-mono text-[10px] tracking-wider hover:bg-primary/10 transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            RETRY
          </button>
        </div>
      );
    }

    return filteredPlaces.map((place) => {
      const cfg = getTypeConfig(place.place_type);
      const { Icon: IconComponent, statusClass } = cfg;
      const distanceVal = place.distance_km ? `${place.distance_km.toFixed(1)} KM` : '0.0 KM';
      const updatedMeta = getLastUpdatedMeta(place.last_synced);
      const confidenceValue = Math.max(0, Math.min(1, Number(place.data_confidence ?? 0.4)));

      return (
        <div
          key={place.id}
          onClick={() => navigate(`/dashboard/place/${place.id}${currentQuery}`)}
          className="glass-panel p-3.5 rounded-[8px] border border-white/5 hover:border-primary/20 hover:shadow-[0_0_8px_rgba(232,160,32,0.1)] transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between gap-3 overflow-hidden">
            <div className="flex items-center gap-3 overflow-hidden">
              <div className={`p-2.5 rounded-[8px] bg-white/3 border border-white/5 flex-shrink-0 group-hover:scale-105 transition-transform ${statusClass}`}>
                <IconComponent className="w-4 h-4" />
              </div>
              <div className="truncate">
                <h3 className="font-space font-semibold text-sm text-white truncate leading-snug">{place.name.toUpperCase()}</h3>
                <div className="font-mono text-[9px] mt-0.5 tracking-wider">
                  STATUS: <span className={statusClass}>{cfg.label}</span>
                </div>
              </div>
            </div>
            <div className="text-right pl-2 flex-shrink-0">
              <div className="font-mono text-[10px] text-primary font-bold">{distanceVal}</div>
              <div className={`font-mono text-[9px] ${updatedMeta.toneClass}`}>{updatedMeta.label}</div>
            </div>
          </div>

          <div className="mt-2 flex items-center justify-between gap-2 text-[9px] font-mono">
            {place.is_verified ? (
              <div className="flex items-center gap-1 text-primary">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>VERIFIED</span>
              </div>
            ) : (
              <div className="flex items-center gap-1 text-primary">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>COMMUNITY DATA</span>
              </div>
            )}
            <span className="text-textTertiary">Confidence {(confidenceValue * 100).toFixed(0)}%</span>
          </div>

          {updatedMeta.warning && <div className="mt-1 text-[9px] font-mono text-danger">{updatedMeta.warning}</div>}
          <div className="mt-2 h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
            <div className={`h-full ${confidenceTone(confidenceValue)}`} style={{ width: `${confidenceValue * 100}%` }} />
          </div>
        </div>
      );
    });
  };

  const renderOfflineList = () => {
    if (offlineIncidents.length === 0) {
      return (
        <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center text-textTertiary font-mono text-[10px]">
          No cached data. Move to an area with connectivity.
        </div>
      );
    }
    return offlineIncidents.map((incident) => (
      <div key={incident.id} className="glass-panel p-3.5 rounded-[8px] border border-white/5 hover:border-danger/25 transition-all opacity-80 cursor-default select-none relative">
        <div className="flex justify-between items-start mb-2">
          <span className="bg-primary/10 border border-primary/20 text-primary text-[8px] font-mono tracking-widest px-2 py-0.5 rounded uppercase font-bold">CACHED</span>
          <span className="font-mono text-[9px] text-textTertiary">{incident.timestamp}</span>
        </div>
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2.5 rounded-[8px] bg-white/2 text-danger flex-shrink-0">
            {incident.type === 'accident' ? <ShieldAlert className="w-4 h-4" /> :
             incident.type === 'towing' ? <Truck className="w-4 h-4" /> : <MapPin className="w-4 h-4" />}
          </div>
          <div>
            <h3 className="font-space font-bold text-xs text-white">{incident.name}</h3>
            <p className="font-body text-[10px] text-textSecondary leading-none mt-1">{incident.location}</p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 border-t border-white/5 pt-2 font-mono text-[9.5px]">
          <div><span className="text-textTertiary mr-1">UNIT:</span><span className="text-white font-bold">{incident.unit}</span></div>
          <div className="text-right">
            {incident.eta
              ? <><span className="text-textTertiary mr-1">ETA:</span><span className="text-primary font-bold">{incident.eta}</span></>
              : <><span className="text-textTertiary mr-1">STATUS:</span><span className="text-danger font-bold">{incident.status}</span></>}
          </div>
        </div>
      </div>
    ));
  };

  // Issue 4 — Telemetry panel
  const renderTelemetryTab = () => (
    <div className="w-full md:w-[380px] bg-black border-b md:border-b-0 md:border-r border-white/10 flex flex-col overflow-hidden z-10 flex-shrink-0">
      <div className="px-4 py-3.5 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CloudLightning className="w-4 h-4 text-primary" />
          <span className="font-bebas text-xl tracking-wider text-primary">TELEMETRY</span>
        </div>
        {telemetryLoading && <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />}
      </div>
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {!onlineStatus ? (
          <div className="text-center font-mono text-[10px] text-textTertiary py-8">Telemetry unavailable offline</div>
        ) : (
          <>
            {/* NLU Model */}
            <div className="glass-panel rounded-[8px] p-3.5 border border-white/5">
              <div className="font-mono text-[9px] text-textTertiary tracking-widest mb-2 uppercase flex items-center gap-1.5">
                <Zap className="w-3 h-3" /> NLU Model
              </div>
              <div className="font-mono text-xs text-white">
                {telemetryData?.nlu_model ?? 'XLM-RoBERTa (interim) · BART fallback active'}
              </div>
            </div>

            {/* Last Inference */}
            <div className="glass-panel rounded-[8px] p-3.5 border border-white/5">
              <div className="font-mono text-[9px] text-textTertiary tracking-widest mb-2 uppercase flex items-center gap-1.5">
                <Activity className="w-3 h-3" /> Last Inference
              </div>
              {lastInference ? (
                <div className="font-mono text-xs text-white">
                  {lastInference.ms}ms &nbsp;·&nbsp;
                  <span className="text-primary">{String(lastInference.intent).toUpperCase()}</span>
                  &nbsp;·&nbsp;
                  <span className={lastInference.triage === 'P1' ? 'text-danger' : lastInference.triage === 'P2' ? 'text-primary' : 'text-safe'}>
                    {lastInference.triage}
                  </span>
                </div>
              ) : (
                <div className="font-mono text-xs text-textTertiary">No triage run this session</div>
              )}
            </div>

            {/* Places in DB */}
            <div className="glass-panel rounded-[8px] p-3.5 border border-white/5">
              <div className="font-mono text-[9px] text-textTertiary tracking-widest mb-2 uppercase flex items-center gap-1.5">
                <Database className="w-3 h-3" /> Places in DB
              </div>
              <div className="font-mono text-2xl font-bold text-primary">
                {telemetryLoading ? '—' : (telemetryData?.places_count ?? activeOps)}
              </div>
              <div className="font-mono text-[9px] text-textTertiary mt-1">verified emergency resources</div>
            </div>

            {/* SOS Logs Today */}
            <div className="glass-panel rounded-[8px] p-3.5 border border-white/5">
              <div className="font-mono text-[9px] text-textTertiary tracking-widest mb-2 uppercase flex items-center gap-1.5">
                <ShieldAlert className="w-3 h-3" /> SOS Logs Today
              </div>
              <div className="font-mono text-2xl font-bold text-danger">
                {telemetryLoading ? '—' : (telemetryData?.sos_today ?? 0)}
              </div>
              <div className="font-mono text-[9px] text-textTertiary mt-1">emergency triggers since midnight</div>
            </div>

            {/* Offline Cache */}
            <div className="glass-panel rounded-[8px] p-3.5 border border-white/5">
              <div className="font-mono text-[9px] text-textTertiary tracking-widest mb-2 uppercase flex items-center gap-1.5">
                <Clock className="w-3 h-3" /> Offline Cache
              </div>
              <div className="font-mono text-xs text-white">
                {cacheAge != null
                  ? `${cacheAge} mins old · ${activeOps} places cached`
                  : fromCache
                    ? `Active · ${activeOps} places cached`
                    : 'Cache warm · ready for offline'}
              </div>
            </div>

            {/* Backend version */}
            {telemetryData?.version && (
              <div className="text-center font-mono text-[9px] text-textTertiary mt-2">
                Backend v{telemetryData.version} · DB {telemetryData.db}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );

  // Issue 5 — Fleet placeholder
  const renderFleetTab = () => (
    <div className="w-full md:w-[380px] bg-black border-b md:border-b-0 md:border-r border-white/10 flex flex-col overflow-hidden z-10 flex-shrink-0">
      <div className="px-4 py-3.5 border-b border-white/10 flex items-center gap-2">
        <Truck className="w-4 h-4 text-primary" />
        <span className="font-bebas text-xl tracking-wider text-primary">FLEET MANAGEMENT</span>
      </div>
      <div className="flex-1 p-4 flex flex-col gap-4">
        <div className="text-center py-4">
          <div className="font-mono text-[10px] text-textSecondary leading-relaxed">
            Vehicle tracking integration — coming in v2.0
          </div>
        </div>

        {/* Demo card */}
        <div className="glass-panel rounded-[8px] p-4 border border-white/10 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Ambulance className="w-4 h-4 text-safe" />
              <span className="font-space font-bold text-sm text-white">AMB-09</span>
            </div>
            <span className="px-2.5 py-0.5 rounded-pill text-[9px] font-mono font-bold border border-safe/40 text-safe">AVAILABLE</span>
          </div>
          <div className="flex items-center justify-between font-mono text-[9.5px]">
            <span className="text-textTertiary">LAST SEEN</span>
            <span className="text-white">8 min ago</span>
          </div>
          <div className="flex items-center justify-between font-mono text-[9.5px]">
            <span className="text-textTertiary">OPERATOR</span>
            <span className="text-white">Unit 4 · Dispatch Active</span>
          </div>
          <div className="h-1 w-full bg-white/10 rounded-full overflow-hidden">
            <div className="h-full bg-safe" style={{ width: '80%' }} />
          </div>
          <div className="font-mono text-[9px] text-textTertiary">Capacity 80%</div>
        </div>

        <div className="flex items-center gap-2 px-3 py-3 rounded-[8px] border border-dashed border-white/10 text-textTertiary font-mono text-[9px]">
          <Info className="w-3.5 h-3.5 flex-shrink-0" />
          Connect your fleet provider API in Settings to enable live vehicle tracking.
        </div>
      </div>
    </div>
  );

  // History tab (existing data)
  const renderHistoryTab = () => (
    <div className="w-full md:w-[380px] bg-black border-b md:border-b-0 md:border-r border-white/10 flex flex-col overflow-hidden z-10 flex-shrink-0">
      <div className="px-4 py-3.5 border-b border-white/10 flex items-center gap-2">
        <FileText className="w-4 h-4 text-primary" />
        <span className="font-bebas text-xl tracking-wider text-primary">HISTORY</span>
      </div>
      <div className="flex-1 p-4 flex flex-col items-center justify-center text-center gap-3">
        <div className="w-12 h-12 rounded-full bg-white/5 border border-white/10 flex items-center justify-center">
          <FileText className="w-5 h-5 text-textTertiary" />
        </div>
        <div className="font-mono text-[10px] text-textTertiary">No SOS history this session</div>
      </div>
    </div>
  );

  const renderTriageCard = () => (
    <div className="glass-panel rounded-[8px] p-3 border border-primary/20 text-left flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[10px] tracking-widest text-textSecondary uppercase">{String(triageResult.intent).toUpperCase()}</span>
        <span className={`px-2.5 py-0.5 rounded-pill text-[10px] font-mono font-bold tracking-widest border ${
          triageResult.triage === 'P1' ? 'text-white bg-danger border-danger' :
          triageResult.triage === 'P2' ? 'text-black bg-primary border-primary' :
          'text-black bg-safe border-safe'
        }`}>
          {triageResult.triage === 'P1' ? 'P1 CRITICAL' : triageResult.triage === 'P2' ? 'P2 SERIOUS' : 'P3 MINOR'}
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {Object.entries(triageResult.slots || {}).length > 0
          ? Object.entries(triageResult.slots || {}).map(([key, value]) => {
              const k = key.toUpperCase();
              const emoji = k === 'LOCATION' || k === 'LOCATION_MENTION' ? '📍' : k === 'CASUALTY_COUNT' || k === 'CASUALTIES' ? '👥' : k === 'HAZARD_TYPE' || k === 'HAZARD' ? '🔥' : '🏷️';
              return (
                <span key={key} className="px-2 py-0.5 rounded-pill text-[9px] font-mono border border-white/10 text-textSecondary flex items-center gap-1">
                  <span>{emoji}</span><span>{String(value)}</span>
                </span>
              );
            })
          : <span className="text-[10px] font-mono text-textTertiary">No slots extracted yet.</span>}
      </div>
      {triageResult.follow_up_question && (
        <div className="rounded-[6px] bg-primary/10 border border-primary/30 px-2.5 py-2 text-[10px] font-mono text-primary">
          ⚠ {triageResult.follow_up_question}
        </div>
      )}
      {triageResult.ready_to_dispatch && (
        <div className="rounded-[6px] bg-safe/10 border border-safe/30 px-2.5 py-2 text-[10px] font-mono text-safe flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5" />
          Dispatching nearest services...
        </div>
      )}
      {triageResult.cap_alert && (
        <div className="border border-white/10 rounded-[8px] overflow-hidden">
          <button
            onClick={() => setCapExpanded(v => !v)}
            className="w-full px-2.5 py-2 flex items-center justify-between text-[10px] font-mono tracking-wider text-white/90 bg-white/5"
          >
            <span>CAP v1.2 Alert</span>
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${capExpanded ? 'rotate-180' : ''}`} />
          </button>
          {capExpanded && (
            <div className="p-2 text-[9px] leading-relaxed max-h-52 overflow-auto text-textSecondary bg-black/40 space-y-1">
              {triageResult.cap_alert.info?.[0]?.urgency && <div>urgency: <span className="text-white/70">{triageResult.cap_alert.info[0].urgency}</span></div>}
              {triageResult.cap_alert.info?.[0]?.severity && <div>severity: <span className="text-white/70">{triageResult.cap_alert.info[0].severity}</span></div>}
              {triageResult.cap_alert.info?.[0]?.certainty && <div>certainty: <span className="text-white/70">{triageResult.cap_alert.info[0].certainty}</span></div>}
            </div>
          )}
        </div>
      )}
    </div>
  );

  const leftPanel = () => {
    if (!id) {
      if (activeTab === 'dispatch') return renderDispatchTab();
      if (activeTab === 'telemetry') return renderTelemetryTab();
      if (activeTab === 'fleet') return renderFleetTab();
      if (activeTab === 'history') return renderHistoryTab();
    }
    return null;
  };

  return (
    <div className="w-full min-h-screen flex flex-col bg-black text-white font-body selection:bg-primary selection:text-black overflow-hidden">

      {/* Offline Banner */}
      {!onlineStatus && (
        <div className="w-full h-[44px] bg-primary text-black font-bebas text-sm tracking-wider flex items-center justify-center gap-2 z-50 animate-pulse flex-shrink-0">
          <WifiOff className="w-4 h-4" />
          <span>YOU ARE OFFLINE - SHOWING CACHED RESULTS</span>
        </div>
      )}

      {/* Main layout */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">

        {/* ── SIDEBAR (desktop) / BOTTOM NAV (mobile) ─────────────────────── */}
        {/* Desktop sidebar */}
        <aside className="hidden md:flex w-[240px] flex-shrink-0 bg-black border-r border-white/10 flex-col justify-between p-4 z-20">
          <div className="flex flex-col gap-6">
            <Link to="/" className="font-space font-bold text-xl tracking-[0.2em] text-primary hover:opacity-90 select-none">ROADSOS</Link>
            <div className="text-left font-mono">
              <div className="text-[9px] text-textSecondary uppercase tracking-widest leading-none">COMMAND CENTER</div>
              {/* Issue 2 — real activeOps */}
              <div className="text-sm text-primary font-bold mt-1">Active Ops: {onlineStatus ? activeOps : '— (OFFLINE)'}</div>
              <div className="mt-1 flex items-center gap-2">
                {demoMode && <span className="px-2 py-0.5 rounded-pill border border-primary/40 text-primary text-[9px] tracking-widest">DEMO MODE</span>}
                {onlineStatus && fromCache && <span className="px-2 py-0.5 rounded-pill border border-white/20 text-textSecondary text-[9px] tracking-widest">CACHED</span>}
              </div>
            </div>
            <nav className="flex flex-col gap-1">
              {[
                { key: 'dispatch',  label: 'Dispatch',  Icon: Activity },
                { key: 'telemetry', label: 'Telemetry', Icon: CloudLightning },
                { key: 'fleet',     label: 'Fleet',     Icon: Truck },
                { key: 'history',   label: 'History',   Icon: FileText },
              ].map(({ key, label, Icon }) => (
                <button
                  key={key}
                  onClick={() => setActiveTab(key)}
                  className={`px-3 py-2.5 rounded-[8px] font-mono text-xs tracking-wider flex items-center gap-3 transition-all ${
                    activeTab === key ? 'bg-primary text-black font-bold' : 'text-textSecondary hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{label}</span>
                </button>
              ))}
            </nav>
          </div>
          {/* Issue 10 — SOS button at bottom of sidebar */}
          <button
            onClick={() => setSosActive(true)}
            className={`w-full py-3 text-white font-bebas text-lg tracking-wider rounded-pill transition-all active:scale-95 flex items-center justify-center gap-2 mt-4 ${
              onlineStatus
                ? 'bg-primary hover:bg-primary/95 text-black shadow-[0_0_10px_rgba(232,160,32,0.2)]'
                : 'bg-danger hover:bg-danger/95 shadow-[0_0_12px_rgba(230,57,70,0.3)]'
            }`}
          >
            <ShieldAlert className="w-5 h-5 animate-pulse" />
            TRIGGER SOS
          </button>
        </aside>

        {/* ── CONTENT AREA ─────────────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden relative">

          {/* Left panel (dynamic based on tab) */}
          {leftPanel()}

          {/* MAP AREA */}
          <div className="flex-1 h-full relative overflow-hidden bg-black min-h-[300px] md:min-h-0">

            {/* CACHED watermark overlay */}
            {!onlineStatus && (
              <div className="absolute inset-0 z-30 flex items-center justify-center pointer-events-none overflow-hidden bg-black/10">
                <div className="absolute w-[450px] h-[450px] border border-white/5 rounded-full flex items-center justify-center">
                  <div className="w-[300px] h-[300px] border border-white/5 rounded-full flex items-center justify-center">
                    <div className="w-[150px] h-[150px] border border-white/5 rounded-full" />
                  </div>
                </div>
                <div className="font-bebas text-[110px] tracking-[0.25em] text-white/5 select-none transform -rotate-[20deg]">CACHED</div>
              </div>
            )}

            <MapContainer
              center={[storeLat, storeLng]}
              zoom={mapZoom}
              scrollWheelZoom={true}
              zoomControl={false}
              className="w-full h-full z-10"
            >
              <MapController center={{ lat: storeLat, lng: storeLng }} zoom={mapZoom} />
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              />
              <Marker position={[storeLat, storeLng]} icon={userIcon} />
              {onlineStatus && allPlaces.map((place) => (
                <Marker
                  key={place.id}
                  position={[place.latitude, place.longitude]}
                  icon={getCustomMarkerIcon(place)}
                  eventHandlers={{ click: () => navigate(`/dashboard/place/${place.id}${currentQuery}`) }}
                />
              ))}
              {onlineStatus && nearestHospital && (
                <Polyline
                  positions={[[storeLat, storeLng], [nearestHospital.latitude, nearestHospital.longitude]]}
                  pathOptions={{ color: '#3A86FF', dashArray: '6, 8', weight: 3 }}
                />
              )}
            </MapContainer>

            {/* TOP BAR overlay */}
            <div className="absolute top-4 left-4 right-4 z-20 flex justify-between items-center pointer-events-none">
              <div />
              <div className="flex items-center gap-3 pointer-events-auto">
                {/* Issue 1 — live city/coords */}
                <div className="glass-panel px-3 py-1.5 rounded-[6px] font-mono text-[10px] text-white flex items-center gap-2">
                  <MapPin className="w-3.5 h-3.5 text-primary" />
                  <span>{cityName}</span>
                </div>
                <div className="glass-panel px-3 py-1.5 rounded-[6px] font-mono text-[10px] text-white flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${onlineStatus ? 'bg-safe animate-pulse' : 'bg-danger'}`} />
                  <span>{onlineStatus ? 'OPERATIONAL' : 'NO CONNECTION'}</span>
                </div>
                <div className="flex gap-1.5">
                  <button
                    onClick={() => setToast('No new notifications', 'info')}
                    className="p-2 bg-neutral-950/80 hover:bg-neutral-950 border border-white/10 hover:border-primary/30 rounded-[6px] text-textSecondary hover:text-white transition-colors"
                  >
                    <Bell className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setToast('Settings command suspended', 'info')}
                    className="p-2 bg-neutral-950/80 hover:bg-neutral-950 border border-white/10 hover:border-primary/30 rounded-[6px] text-textSecondary hover:text-white transition-colors"
                  >
                    <Settings className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            {/* Issue 1 — GRID SEC coordinates HUD */}
            <div className="absolute top-[80px] right-4 z-20 glass-panel p-3.5 rounded-[8px] text-right pointer-events-none select-none">
              <div className="font-bebas text-lg tracking-wider text-primary leading-none uppercase">{cityName}</div>
              <div className="font-mono text-[10px] text-textSecondary mt-1 leading-none">
                GRID SEC: {storeLat.toFixed(4)}° N, {storeLng.toFixed(4)}° E
              </div>
            </div>

            {/* SOS BUTTON — bottom center */}
            <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 z-20 flex flex-col items-center gap-2 pointer-events-auto">
              <div className="relative w-[76px] h-[76px] flex items-center justify-center">
                <div className="absolute inset-0 bg-danger rounded-full pulsing-ring-1" />
                <div className="absolute inset-0 bg-danger rounded-full pulsing-ring-2" />
                <button
                  onMouseDown={startHoldSos}
                  onMouseUp={endHoldSos}
                  onMouseLeave={endHoldSos}
                  onTouchStart={startHoldSos}
                  onTouchEnd={endHoldSos}
                  className={`relative w-[72px] h-[72px] rounded-full flex items-center justify-center text-white border border-white/20 transition-all select-none shadow-[0_0_24px_rgba(230,57,70,0.5)] ${
                    isHoldingSos ? 'bg-danger/60 scale-95' : 'bg-danger hover:scale-105 active:scale-95'
                  }`}
                  aria-label="Hold for Emergency SOS"
                >
                  <span className="font-mono text-3xl font-bold animate-pulse text-white">*</span>
                </button>
              </div>
              <div className="font-mono text-[9px] text-primary tracking-widest leading-none bg-black/60 px-2 py-0.5 rounded border border-white/5">
                {isHoldingSos ? 'HOLDING 1.5s...' : 'HOLD FOR EMERGENCY'}
              </div>
            </div>

            {/* SHARE LOCATION — bottom right */}
            <div className="absolute bottom-6 right-4 z-20 pointer-events-auto">
              <button
                onClick={handleShareLocation}
                className="glass-panel px-4 py-2 rounded-pill font-mono text-[10px] tracking-wider text-white hover:text-primary transition-all border border-white/10 hover:border-primary/40 shadow-lg flex items-center gap-2 uppercase font-bold"
              >
                <Navigation className="w-3.5 h-3.5 text-primary rotate-45" />
                SHARE LOCATION
              </button>
            </div>

            {/* Offline context card — bottom left */}
            {!onlineStatus && (
              <div className="absolute bottom-6 left-4 z-20 w-[320px] glass-panel p-4 rounded-[8px] border border-danger/30 hover:border-primary/20 transition-all shadow-xl pointer-events-auto flex flex-col gap-2.5">
                <div className="flex items-center gap-2 text-primary">
                  <Info className="w-4 h-4" />
                  <span className="font-bebas text-sm tracking-wider uppercase font-bold">OFFLINE CONTEXT</span>
                </div>
                <p className="font-body text-[10.5px] text-textSecondary leading-normal text-left">
                  Current data reflects the state of dispatch as of {new Date().toLocaleTimeString()}. AI predictive routing and real-time telemetry are suspended.
                </p>
                <div className="flex items-center justify-between border-t border-white/5 pt-2 font-mono text-[9px]">
                  <span className="text-textTertiary">SYNC STATUS:</span>
                  <span className="flex items-center gap-1.5 text-danger font-bold">
                    <span className="w-1.5 h-1.5 rounded-full bg-danger animate-pulse" />
                    NO LINK
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* PLACE DETAIL — right panel */}
          {id && (
            <div className="w-full md:w-[380px] bg-black border-t md:border-t-0 md:border-l border-white/10 flex flex-col overflow-hidden z-10 flex-shrink-0 animate-in slide-in-from-right duration-300">
              <PlaceDetail />
            </div>
          )}
        </div>
      </div>

      {/* Issue 8 — Mobile bottom navigation bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-black/95 backdrop-blur-md border-t border-white/10 flex items-center justify-around px-2 py-2">
        {[
          { key: 'dispatch',  label: 'Dispatch',  Icon: Activity },
          { key: 'telemetry', label: 'Telemetry', Icon: CloudLightning },
          { key: 'fleet',     label: 'Fleet',     Icon: Truck },
          { key: 'history',   label: 'History',   Icon: FileText },
        ].map(({ key, label, Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex flex-col items-center gap-1 px-3 py-1.5 rounded-[8px] transition-all ${
              activeTab === key ? 'text-primary' : 'text-textTertiary hover:text-white'
            }`}
          >
            <Icon className="w-5 h-5" />
            <span className="font-mono text-[8px] tracking-wider">{label.toUpperCase()}</span>
          </button>
        ))}
        {/* Centered SOS trigger */}
        <button
          onClick={() => setSosActive(true)}
          className="absolute left-1/2 -translate-x-1/2 -top-5 w-12 h-12 rounded-full bg-danger border-2 border-black flex items-center justify-center shadow-[0_0_16px_rgba(230,57,70,0.5)]"
        >
          <ShieldAlert className="w-5 h-5 text-white animate-pulse" />
        </button>
      </nav>
    </div>
  );
}
