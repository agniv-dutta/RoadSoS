import { create } from 'zustand';

// Simple base32 geohash encoder
export function encodeGeohash(latitude, longitude, precision = 5) {
  const BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz";
  let isEven = true;
  let latMin = -90.0, latMax = 90.0;
  let lonMin = -180.0, lonMax = 180.0;
  let geohash = "";
  let bit = 0;
  let ch = 0;

  while (geohash.length < precision) {
    let mid;
    if (isEven) {
      mid = (lonMin + lonMax) / 2;
      if (longitude > mid) {
        ch |= (1 << (4 - bit));
        lonMin = mid;
      } else {
        lonMax = mid;
      }
    } else {
      mid = (latMin + latMax) / 2;
      if (latitude > mid) {
        ch |= (1 << (4 - bit));
        latMin = mid;
      } else {
        latMax = mid;
      }
    }

    isEven = !isEven;
    if (bit < 4) {
      bit++;
    } else {
      geohash += BASE32[ch];
      bit = 0;
      ch = 0;
    }
  }
  return geohash;
}

// Initial mock data to seed for offline demonstration
const MOCK_OFFLINE_INCIDENTS = [
  {
    id: 1,
    type: "accident",
    name: "MVA - Zone 4",
    location: "Interstate 80 East",
    unit: "AMB-09",
    eta: "8m 42s",
    status: null,
    timestamp: "14:22 PM"
  },
  {
    id: 2,
    type: "towing",
    name: "Disablement",
    location: "Bridge Street Tunnel",
    unit: "TOW-21",
    eta: null,
    status: "STALLED",
    timestamp: "14:15 PM"
  },
  {
    id: 3,
    type: "medical",
    name: "Wellness Check",
    location: "Main St. Plaza",
    unit: "MED-02",
    eta: "12m 10s",
    status: "RESPONDING",
    timestamp: "14:02 PM"
  }
];

export const useSosStore = create((set, get) => ({
  userLocation: { lat: 19.0760, lng: 72.8777 }, // Mumbai default
  onlineStatus: navigator.onLine,
  sosActive: false,
  nearbyPlaces: [],
  selectedPlace: null,
  activeSession: null,
  toast: null,
  offlineIncidents: [],

  setSosActive: (sosActive) => set({ sosActive }),
  
  setOnlineStatus: (onlineStatus) => {
    set({ onlineStatus });
    if (!onlineStatus) {
      get().loadOfflineCache();
    }
  },

  setUserLocation: (lat, lng) => {
    set({ userLocation: { lat, lng } });
    // Always seed/update cache for current location's geohash
    const geohash = encodeGeohash(lat, lng, 5);
    const key = `sos_cache_${geohash}`;
    if (!localStorage.getItem(key)) {
      localStorage.setItem(key, JSON.stringify(MOCK_OFFLINE_INCIDENTS));
    }
    // Reload cache
    if (!get().onlineStatus) {
      get().loadOfflineCache();
    }
  },

  setNearbyPlaces: (nearbyPlaces) => set({ nearbyPlaces }),
  setSelectedPlace: (selectedPlace) => set({ selectedPlace }),
  setActiveSession: (activeSession) => set({ activeSession }),

  setToast: (message, type = 'error') => {
    set({ toast: { message, type } });
    // Auto-dismiss toast
    setTimeout(() => {
      const currentToast = get().toast;
      if (currentToast && currentToast.message === message) {
        set({ toast: null });
      }
    }, 4000);
  },

  clearToast: () => set({ toast: null }),

  loadOfflineCache: () => {
    const { userLocation } = get();
    const geohash = encodeGeohash(userLocation.lat, userLocation.lng, 5);
    const key = `sos_cache_${geohash}`;
    const cachedData = localStorage.getItem(key);
    if (cachedData) {
      set({ offlineIncidents: JSON.parse(cachedData) });
    } else {
      // Seed on the fly
      localStorage.setItem(key, JSON.stringify(MOCK_OFFLINE_INCIDENTS));
      set({ offlineIncidents: MOCK_OFFLINE_INCIDENTS });
    }
  }
}));
