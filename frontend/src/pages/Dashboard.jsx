import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, Link, useLocation } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { useSosStore } from '../store/useSosStore';
import { api } from '../api/client';
import PlaceDetail from './PlaceDetail';
import { 
  Radio, Wifi, WifiOff, Bell, Settings, Search, MapPin, 
  Flame, Shield, Truck, Cross, ChevronRight, Share, Navigation,
  CloudLightning, AlertCircle, Info, ShieldAlert, HeartHandshake,
  Activity, Users, FileText
} from 'lucide-react';

// Custom Map center controller helper
function MapController({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView([center.lat, center.lng], zoom || map.getZoom());
    }
  }, [center, zoom, map]);
  return null;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const location = useLocation();
  const { id } = useParams(); // For Screen 4 PlaceDetail routing
  
  const { 
    userLocation, setUserLocation,
    onlineStatus, setOnlineStatus,
    sosActive, setSosActive,
    nearbyPlaces, setNearbyPlaces,
    selectedPlace, setSelectedPlace,
    toast, setToast,
    offlineIncidents, loadOfflineCache
  } = useSosStore();

  const [activeTab, setActiveTab] = useState('dispatch'); // 'dispatch', 'telemetry', 'fleet', 'history'
  const [activeFilter, setActiveFilter] = useState('all'); // 'all', 'hospital', 'police'
  const [searchQuery, setSearchQuery] = useState('');
  const [mapZoom, setMapZoom] = useState(13);
  const [isHoldingSos, setIsHoldingSos] = useState(false);
  const holdTimerRef = useRef(null);

  // Set Title on Mount
  useEffect(() => {
    document.title = "RoadSoS — Tactical Dashboard";
  }, []);

  // Sync / Fetch Places on mount or coordinate changes
  useEffect(() => {
    if (!onlineStatus) {
      loadOfflineCache();
      return;
    }

    const fetchPlaces = async () => {
      try {
        const data = await api.getNearby(userLocation.lat, userLocation.lng, 10);
        if (data && data.results) {
          setNearbyPlaces(data.results);
        }
      } catch (err) {
        console.error("Failed to load nearby places:", err);
      }
    };

    fetchPlaces();
  }, [userLocation, onlineStatus, setNearbyPlaces, loadOfflineCache]);

  // Adjust map configurations based on route
  useEffect(() => {
    if (id) {
      // Screen 4 is active: Set zoom 14 and focus on the place coordinates if loaded
      const place = nearbyPlaces.find(p => p.id === parseInt(id));
      if (place) {
        setSelectedPlace(place);
        setMapZoom(14);
      }
    } else {
      setSelectedPlace(null);
      setMapZoom(13);
    }
  }, [id, nearbyPlaces, setSelectedPlace]);

  // Handle network online/offline listeners
  useEffect(() => {
    const handleOnline = () => {
      setOnlineStatus(true);
      setToast("Connection restored — synchronizing command grid", "success");
    };
    const handleOffline = () => {
      setOnlineStatus(false);
      setToast("Backend unavailable — operating in offline mode", "error");
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [setOnlineStatus, setToast]);

  // Geolocation tracker
  const handleShareLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          setUserLocation(latitude, longitude);
          setToast("Location synchronized successfully", "success");
        },
        () => {
          setToast("Unable to fetch current location. Check browser settings.", "error");
        }
      );
    } else {
      setToast("Geolocation is not supported by your browser.", "error");
    }
  };

  // SOS Hold Trigger
  const startHoldSos = () => {
    setIsHoldingSos(true);
    holdTimerRef.current = setTimeout(() => {
      setIsHoldingSos(false);
      setSosActive(true);
    }, 1500); // 1.5 second hold to activate
  };

  const endHoldSos = () => {
    setIsHoldingSos(false);
    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current);
    }
  };

  // Filters results list based on filter tab and search box
  const filteredPlaces = nearbyPlaces.filter(place => {
    // Type Filter
    if (activeFilter === 'hospital' && place.place_type !== 'hospital' && place.place_type !== 'trauma_center') {
      return false;
    }
    if (activeFilter === 'police' && place.place_type !== 'police') {
      return false;
    }
    
    // Search Query
    if (searchQuery.trim() !== '') {
      return place.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
             (place.address && place.address.toLowerCase().includes(searchQuery.toLowerCase()));
    }
    
    return true;
  });

  // Calculate coordinates string
  const locationName = userLocation.lat.toFixed(2) === "19.08" ? "MUM_IN" : "DEL_IN";
  const regionName = userLocation.lat.toFixed(2) === "19.08" ? "MUMBAI" : "DELHI";

  // Identify nearest hospital coordinates to render routing line
  const hospitals = nearbyPlaces.filter(p => p.place_type === 'hospital');
  const nearestHospital = hospitals.length > 0 ? hospitals[0] : null;

  // Custom marker icon creation mapping
  const getCustomMarkerIcon = (place) => {
    let color = '#E8A020'; // Default amber
    let text = 'T';

    if (place.place_type === 'hospital' || place.place_type === 'trauma_center') {
      color = '#E63946'; // Red
      text = '+';
    } else if (place.place_type === 'police') {
      color = '#3A86FF'; // Blue
      text = 'P';
    } else if (place.place_type === 'towing') {
      color = '#E8A020'; // Amber
      text = 'T';
    } else if (place.place_type === 'fire_station') {
      color = '#E63946'; // Red
      text = 'F';
    }

    const isAmbulance = place.place_type === 'hospital' && place.name.toLowerCase().includes('general');
    const animClass = isAmbulance ? 'animate-bounce-gentle' : '';

    return L.divIcon({
      html: `<div class="w-8 h-8 rounded-full border border-white/20 bg-black flex items-center justify-center shadow-lg transition-transform hover:scale-110 ${animClass}" style="box-shadow: 0 0 8px ${color}50">
        <span style="color: ${color}" class="text-sm font-bold font-mono select-none">${text}</span>
      </div>`,
      className: 'custom-marker',
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });
  };

  const userIcon = L.divIcon({
    html: `<div class="pulsing-marker"></div>`,
    className: 'user-marker',
    iconSize: [16, 16],
    iconAnchor: [8, 8]
  });

  return (
    <div className="w-full min-h-screen flex flex-col md:flex-row bg-black text-white font-body selection:bg-primary selection:text-black overflow-hidden">
      
      {/* 44px Offline Sticky Banner (Screen 5) */}
      {!onlineStatus && (
        <div className="absolute top-0 left-0 w-full h-[44px] bg-primary text-black font-bebas text-sm tracking-wider flex items-center justify-center gap-2 z-50 animate-pulse">
          <WifiOff className="w-4 h-4" />
          <span>YOU ARE OFFLINE - SHOWING CACHED RESULTS</span>
        </div>
      )}

      {/* Main View Wrapper with offset if offline banner shows */}
      <div className={`w-full h-screen flex flex-col md:flex-row ${!onlineStatus ? 'pt-[44px]' : ''}`}>
        
        {/* SIDEBAR: 240px */}
        <aside className="w-full md:w-[240px] flex-shrink-0 bg-black border-b md:border-b-0 md:border-r border-white/10 flex flex-col justify-between p-4 z-20">
          
          <div className="flex flex-col gap-6">
            {/* Logo */}
            <Link to="/" className="font-space font-bold text-xl tracking-[0.2em] text-primary hover:opacity-90 select-none">
              ROADSOS
            </Link>

            {/* Command HUD */}
            <div className="text-left font-mono">
              <div className="text-[9px] text-textSecondary uppercase tracking-widest leading-none">
                {onlineStatus ? "COMMAND CENTER" : "COMMAND CENTER"}
              </div>
              <div className="text-sm text-primary font-bold mt-1">
                Active Ops: {onlineStatus ? nearbyPlaces.length : '3 (OFFLINE)'}
              </div>
            </div>

            {/* Nav Items */}
            <nav className="flex flex-row md:flex-col gap-1 overflow-x-auto md:overflow-x-visible pb-2 md:pb-0">
              <button 
                onClick={() => { if (onlineStatus) setActiveTab('dispatch'); }}
                disabled={!onlineStatus}
                title={!onlineStatus ? "Unavailable offline" : ""}
                className={`px-3 py-2.5 rounded-pill md:rounded-[8px] font-mono text-xs tracking-wider flex items-center gap-3 transition-all ${
                  activeTab === 'dispatch' 
                    ? 'bg-primary text-black font-bold' 
                    : 'text-textSecondary hover:text-white hover:bg-white/5'
                } ${!onlineStatus ? 'opacity-60 cursor-not-allowed' : ''}`}
              >
                <Activity className="w-4 h-4" />
                <span>Dispatch</span>
              </button>

              <button 
                onClick={() => { if (onlineStatus) setActiveTab('telemetry'); }}
                disabled={!onlineStatus}
                title={!onlineStatus ? "Unavailable offline" : ""}
                className={`px-3 py-2.5 rounded-pill md:rounded-[8px] font-mono text-xs tracking-wider flex items-center gap-3 transition-all ${
                  activeTab === 'telemetry' 
                    ? 'bg-primary text-black font-bold' 
                    : 'text-textSecondary hover:text-white hover:bg-white/5'
                } ${!onlineStatus ? 'opacity-60 cursor-not-allowed' : ''}`}
              >
                <CloudLightning className="w-4 h-4" />
                <span>Telemetry</span>
              </button>

              <button 
                onClick={() => { if (onlineStatus) setActiveTab('fleet'); }}
                disabled={!onlineStatus}
                title={!onlineStatus ? "Unavailable offline" : ""}
                className={`px-3 py-2.5 rounded-pill md:rounded-[8px] font-mono text-xs tracking-wider flex items-center gap-3 transition-all ${
                  activeTab === 'fleet' 
                    ? 'bg-primary text-black font-bold' 
                    : 'text-textSecondary hover:text-white hover:bg-white/5'
                } ${!onlineStatus ? 'opacity-60 cursor-not-allowed' : ''}`}
              >
                <Truck className="w-4 h-4" />
                <span>Fleet</span>
              </button>

              <button 
                onClick={() => { if (onlineStatus) setActiveTab('history'); }}
                disabled={!onlineStatus}
                title={!onlineStatus ? "Unavailable offline" : ""}
                className={`px-3 py-2.5 rounded-pill md:rounded-[8px] font-mono text-xs tracking-wider flex items-center gap-3 transition-all ${
                  activeTab === 'history' 
                    ? 'bg-primary text-black font-bold' 
                    : 'text-textSecondary hover:text-white hover:bg-white/5'
                } ${!onlineStatus ? 'opacity-60 cursor-not-allowed' : ''}`}
              >
                <FileText className="w-4 h-4" />
                <span>History</span>
              </button>
            </nav>
          </div>

          {/* Trigger SOS Button (Bottom) */}
          <button 
            onClick={() => setSosActive(true)}
            className={`w-full py-3 text-white font-bebas text-lg tracking-wider rounded-pill transition-all active:scale-95 flex items-center justify-center gap-2 mt-4 md:mt-0 ${
              onlineStatus 
                ? 'bg-primary hover:bg-primary/95 text-black shadow-[0_0_10px_rgba(232,160,32,0.2)]' 
                : 'bg-danger hover:bg-danger/95 shadow-[0_0_12px_rgba(230,57,70,0.3)]'
            }`}
          >
            <ShieldAlert className="w-5 h-5 animate-pulse" />
            TRIGGER SOS
          </button>
        </aside>

        {/* Dynamic Layout Configuration: LIST LEFT, MAP RIGHT (online) vs MAP LEFT, DETAILS RIGHT (place selected) */}
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden relative">
          
          {/* RESULTS PANEL: 380px (if NOT viewing details page / Screen 4) */}
          {!id ? (
            <div className="w-full md:w-[380px] bg-black border-b md:border-b-0 md:border-r border-white/10 flex flex-col overflow-hidden z-10 flex-shrink-0">
              
              {/* Navbar Search block */}
              <div className="p-4 border-b border-white/10 bg-neutral-950 flex flex-col gap-3">
                <div className="relative">
                  <Search className="w-4 h-4 text-textTertiary absolute left-3 top-3" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="CMD: Search Dispatch Grid..."
                    disabled={!onlineStatus}
                    title={!onlineStatus ? "Unavailable offline" : ""}
                    className={`w-full h-10 pl-9 pr-4 bg-white/3 border border-white/10 rounded-[8px] text-xs font-mono placeholder:text-textTertiary text-white focus:outline-none focus:border-primary focus:shadow-[0_0_8px_rgba(232,160,32,0.25)] transition-all ${
                      !onlineStatus ? 'opacity-60 cursor-not-allowed' : ''
                    }`}
                  />
                </div>
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
                    <span className="glass-panel px-2.5 py-0.5 border border-primary/20 text-primary text-[8px] tracking-widest font-mono font-bold rounded-pill">
                      ● LOCAL CACHE
                    </span>
                  </>
                )}
              </div>

              {/* Filter Tabs (Screen 3) / Cached badges (Screen 5) */}
              {onlineStatus ? (
                <div className="px-4 pb-3 flex gap-2 border-b border-white/10">
                  {['all', 'hospital', 'police'].map((filter) => (
                    <button
                      key={filter}
                      onClick={() => setActiveFilter(filter)}
                      className={`px-3.5 py-1.5 rounded-pill font-mono text-[9.5px] uppercase tracking-wider border transition-all ${
                        activeFilter === filter 
                          ? 'border-primary text-primary font-bold bg-primary/5' 
                          : 'border-white/10 text-textSecondary hover:text-white'
                      }`}
                    >
                      {filter}
                    </button>
                  ))}
                </div>
              ) : null}

              {/* List Content */}
              <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
                {onlineStatus ? (
                  /* Online: List emergency dispatch centers */
                  filteredPlaces.length > 0 ? (
                    filteredPlaces.map((place) => {
                      const isHospital = place.place_type === 'hospital' || place.place_type === 'trauma_center';
                      const isPolice = place.place_type === 'police';
                      const isTowing = place.place_type === 'towing';
                      
                      let IconComponent = Truck;
                      let iconColorClass = 'text-primary';
                      let statusText = 'AVAILABLE';
                      let statusColorClass = 'text-safe';

                      if (isHospital) {
                        IconComponent = HeartHandshake;
                        iconColorClass = 'text-danger';
                        statusText = place.name.toLowerCase().includes('metropolitan') ? 'HIGH CAPACITY' : 'RESPONSIVE';
                        statusColorClass = 'text-danger';
                      } else if (isPolice) {
                        IconComponent = Shield;
                        iconColorClass = 'text-info';
                        statusText = 'ACTIVE DUTY';
                        statusColorClass = 'text-info';
                      } else if (isTowing) {
                        IconComponent = Truck;
                        iconColorClass = 'text-primary';
                        statusText = 'ON ROUTE';
                        statusColorClass = 'text-primary';
                      }

                      const distanceVal = place.distance_km ? `${place.distance_km.toFixed(1)} KM` : '0.0 KM';

                      return (
                        <div 
                          key={place.id}
                          onClick={() => navigate(`/dashboard/place/${place.id}`)}
                          className="glass-panel p-3.5 rounded-[8px] flex items-center justify-between border border-white/5 hover:border-primary/20 hover:shadow-[0_0_8px_rgba(232,160,32,0.1)] transition-all cursor-pointer group"
                        >
                          <div className="flex items-center gap-3 text-left overflow-hidden">
                            <div className={`p-2.5 rounded-[8px] bg-white/3 border border-white/5 flex-shrink-0 group-hover:scale-105 transition-transform ${iconColorClass}`}>
                              <IconComponent className="w-4 h-4" />
                            </div>
                            <div className="truncate">
                              <h3 className="font-space font-semibold text-sm text-white truncate leading-snug">
                                {place.name.toUpperCase()}
                              </h3>
                              <div className="font-mono text-[9px] mt-0.5 tracking-wider">
                                STATUS: <span className={statusColorClass}>{statusText}</span>
                              </div>
                            </div>
                          </div>
                          
                          <div className="font-mono text-[10px] text-primary font-bold flex-shrink-0 pl-2">
                            {distanceVal}
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="w-full h-[150px] flex items-center justify-center font-mono text-[10px] text-textTertiary">
                      NO DISPATCH FOUND IN SECTOR
                    </div>
                  )
                ) : (
                  /* Offline: Cached incident cards (Screen 5) */
                  offlineIncidents.length > 0 ? (
                    offlineIncidents.map((incident) => {
                      return (
                        <div 
                          key={incident.id}
                          className="glass-panel p-3.5 rounded-[8px] border border-white/5 hover:border-danger/25 transition-all opacity-80 cursor-default select-none relative"
                          title="Unavailable offline"
                        >
                          <div className="flex justify-between items-start mb-2">
                            <span className="bg-primary/10 border border-primary/20 text-primary text-[8px] font-mono tracking-widest px-2 py-0.5 rounded uppercase font-bold">
                              CACHED
                            </span>
                            <span className="font-mono text-[9px] text-textTertiary">
                              {incident.timestamp}
                            </span>
                          </div>

                          <div className="flex items-center gap-3 text-left mb-3">
                            <div className="p-2.5 rounded-[8px] bg-white/2 text-danger flex-shrink-0">
                              {incident.type === 'accident' ? <ShieldAlert className="w-4 h-4" /> : 
                               incident.type === 'towing' ? <Truck className="w-4 h-4" /> : <MapPin className="w-4 h-4" />}
                            </div>
                            <div>
                              <h3 className="font-space font-bold text-xs text-white">
                                {incident.name}
                              </h3>
                              <p className="font-body text-[10px] text-textSecondary leading-none mt-1">
                                {incident.location}
                              </p>
                            </div>
                          </div>

                          <div className="grid grid-cols-2 gap-2 border-t border-white/5 pt-2 font-mono text-[9.5px]">
                            <div className="text-left">
                              <span className="text-textTertiary uppercase mr-1">UNIT:</span>
                              <span className="text-white font-bold">{incident.unit}</span>
                            </div>
                            <div className="text-right">
                              {incident.eta ? (
                                <>
                                  <span className="text-textTertiary uppercase mr-1">ETA:</span>
                                  <span className="text-primary font-bold">{incident.eta}</span>
                                </>
                              ) : (
                                <>
                                  <span className="text-textTertiary uppercase mr-1">STATUS:</span>
                                  <span className="text-danger font-bold">{incident.status}</span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center text-textTertiary font-mono text-[10px]">
                      No cached data. Move to an area with connectivity.
                    </div>
                  )
                )}
              </div>
            </div>
          ) : null}

          {/* MAP AREA */}
          <div className="flex-1 h-full relative overflow-hidden bg-black min-h-[400px]">
            
            {/* Dark radar watermark text overlay (Screen 5) */}
            {!onlineStatus && (
              <div className="absolute inset-0 z-30 flex items-center justify-center pointer-events-none overflow-hidden bg-black/10">
                {/* Target circle */}
                <div className="absolute w-[450px] h-[450px] border border-white/5 rounded-full flex items-center justify-center">
                  <div className="w-[300px] h-[300px] border border-white/5 rounded-full flex items-center justify-center">
                    <div className="w-[150px] h-[150px] border border-white/5 rounded-full" />
                  </div>
                </div>
                {/* Text Watermark */}
                <div className="font-bebas text-[110px] tracking-[0.25em] text-white/5 select-none transform -rotate-[20deg]">
                  CACHED
                </div>
              </div>
            )}

            {/* Leaflet MapContainer */}
            <MapContainer 
              center={[userLocation.lat, userLocation.lng]} 
              zoom={mapZoom} 
              scrollWheelZoom={true}
              zoomControl={false}
              className="w-full h-full z-10"
            >
              <MapController center={userLocation} zoom={mapZoom} />
              
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              />

              {/* Pulsing User Location Marker */}
              <Marker position={[userLocation.lat, userLocation.lng]} icon={userIcon} />

              {/* Service Markers */}
              {onlineStatus && nearbyPlaces.map((place) => (
                <Marker 
                  key={place.id}
                  position={[place.latitude, place.longitude]} 
                  icon={getCustomMarkerIcon(place)}
                  eventHandlers={{
                    click: () => navigate(`/dashboard/place/${place.id}`),
                  }}
                />
              ))}

              {/* Dashed blue routing line from user to nearest hospital */}
              {onlineStatus && nearestHospital && (
                <Polyline 
                  positions={[
                    [userLocation.lat, userLocation.lng],
                    [nearestHospital.latitude, nearestHospital.longitude]
                  ]}
                  pathOptions={{ 
                    color: '#3A86FF', 
                    dashArray: '6, 8', 
                    weight: 3 
                  }}
                />
              )}
            </MapContainer>

            {/* TOP BAR / NAV (Floating overlays) */}
            <div className="absolute top-4 left-4 right-4 z-20 flex justify-between items-center pointer-events-none">
              
              {/* Left Top: Breadcrumb CMD Status */}
              <div className="flex gap-2 pointer-events-auto">
                {/* Standard Vite Controls for zoom (optional CSS styled or standard) */}
              </div>

              {/* Right Top HUD Details */}
              <div className="flex items-center gap-3 pointer-events-auto">
                {/* Location Badges */}
                <div className="glass-panel px-3 py-1.5 rounded-[6px] font-mono text-[10px] text-white flex items-center gap-2">
                  <MapPin className="w-3.5 h-3.5 text-primary" />
                  <span>{locationName}</span>
                </div>

                <div className="glass-panel px-3 py-1.5 rounded-[6px] font-mono text-[10px] text-white flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${onlineStatus ? 'bg-safe animate-pulse' : 'bg-danger'}`} />
                  <span>{onlineStatus ? 'OPERATIONAL' : 'NO CONNECTION'}</span>
                </div>

                {/* Notifications & Settings icons */}
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

            {/* MAP OVERLAYS */}
            {/* Top-Right Map Coordinates HUD */}
            <div className="absolute top-[80px] right-4 z-20 glass-panel p-3.5 rounded-[8px] text-right pointer-events-none select-none">
              <div className="font-bebas text-lg tracking-wider text-primary leading-none uppercase">
                {regionName}
              </div>
              <div className="font-mono text-[10px] text-textSecondary mt-1 leading-none">
                GRID SEC: {userLocation.lat.toFixed(4)}° N, {userLocation.lng.toFixed(4)}° E
              </div>
            </div>

            {/* BOTTOM-CENTER: HOLD FOR EMERGENCY BIG SOS BUTTON */}
            <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 z-20 flex flex-col items-center gap-2 pointer-events-auto">
              
              {/* Outer pulsing rings */}
              <div className="relative w-[76px] h-[76px] flex items-center justify-center">
                <div className="absolute inset-0 bg-danger rounded-full pulsing-ring-1" />
                <div className="absolute inset-0 bg-danger rounded-full pulsing-ring-2" />
                
                {/* Main holding button */}
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
                {isHoldingSos ? "HOLDING 1.5s..." : "HOLD FOR EMERGENCY"}
              </div>
            </div>

            {/* BOTTOM-RIGHT: SHARE LOCATION */}
            <div className="absolute bottom-6 right-4 z-20 pointer-events-auto">
              <button
                onClick={handleShareLocation}
                className="glass-panel px-4 py-2 rounded-pill font-mono text-[10px] tracking-wider text-white hover:text-primary transition-all border border-white/10 hover:border-primary/40 shadow-lg flex items-center gap-2 uppercase font-bold"
              >
                <Navigation className="w-3.5 h-3.5 text-primary rotate-45" />
                SHARE LOCATION
              </button>
            </div>

            {/* BOTTOM-LEFT: OFFLINE CONTEXT DETAILS CARD (Screen 5 Only) */}
            {!onlineStatus && (
              <div className="absolute bottom-6 left-4 z-20 w-[320px] glass-panel p-4 rounded-[8px] border border-danger/30 hover:border-primary/20 transition-all shadow-xl pointer-events-auto flex flex-col gap-2.5">
                <div className="flex items-center gap-2 text-primary">
                  <Info className="w-4 h-4" />
                  <span className="font-bebas text-sm tracking-wider uppercase font-bold">
                    OFFLINE CONTEXT
                  </span>
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

          {/* SCREEN 4: DETAILED VIEW RIGHT PANEL: 380px (if viewing place details) */}
          {id ? (
            <div className="w-full md:w-[380px] bg-black border-t md:border-t-0 md:border-l border-white/10 flex flex-col overflow-hidden z-10 flex-shrink-0 animate-in slide-in-from-right duration-300">
              <PlaceDetail />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
