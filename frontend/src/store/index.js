import { create } from 'zustand';

const MAX_TOASTS = 4;
const BASE32 = '0123456789bcdefghjkmnpqrstuvwxyz';
const DEFAULT_OFFLINE_INCIDENTS = [
  {
    id: 1,
    type: 'accident',
    name: 'MVA - Zone 4',
    location: 'Interstate 80 East',
    unit: 'AMB-09',
    eta: '8m 42s',
    status: null,
    timestamp: '14:22 PM',
  },
  {
    id: 2,
    type: 'towing',
    name: 'Disablement',
    location: 'Bridge Street Tunnel',
    unit: 'TOW-21',
    eta: null,
    status: 'STALLED',
    timestamp: '14:15 PM',
  },
  {
    id: 3,
    type: 'medical',
    name: 'Wellness Check',
    location: 'Main St. Plaza',
    unit: 'MED-02',
    eta: '12m 10s',
    status: 'RESPONDING',
    timestamp: '14:02 PM',
  },
];

function geohash5(lat, lng) {
  let geohash = '';
  let bit = 0;
  let ch = 0;
  let isEven = true;
  let minLat = -90;
  let maxLat = 90;
  let minLng = -180;
  let maxLng = 180;

  while (geohash.length < 5) {
    if (isEven) {
      const mid = (minLng + maxLng) / 2;
      if (lng >= mid) {
        ch = (ch << 1) + 1;
        minLng = mid;
      } else {
        ch = ch << 1;
        maxLng = mid;
      }
    } else {
      const mid = (minLat + maxLat) / 2;
      if (lat >= mid) {
        ch = (ch << 1) + 1;
        minLat = mid;
      } else {
        ch = ch << 1;
        maxLat = mid;
      }
    }
    isEven = !isEven;
    bit += 1;
    if (bit === 5) {
      geohash += BASE32[ch];
      bit = 0;
      ch = 0;
    }
  }

  return geohash;
}

function createLocationSlice(set) {
  return {
    lat: 19.076,
    lng: 72.8777,
    accuracy: null,
    locationError: null,
    isLocating: false,
    setLocation: (lat, lng, accuracy = null) =>
      set({
        lat,
        lng,
        accuracy,
        locationError: null,
        userLocation: { lat, lng },
      }),
    setLocationError: (locationError) => set({ locationError }),
    setIsLocating: (isLocating) => set({ isLocating }),
    setAccuracy: (accuracy) => set({ accuracy }),
    setUserLocation: (lat, lng) =>
      set({
        lat,
        lng,
        userLocation: { lat, lng },
      }),
  };
}

function createSosSlice(set) {
  return {
    sosActive: false,
    sosSessionId: null,
    countdown: 5,
    smsSent: false,
    sosPrefillLocation: null,
    startSos: (sessionId = null, prefillLocation = null) =>
      set({
        sosActive: true,
        sosSessionId: sessionId,
        sosPrefillLocation: prefillLocation,
        countdown: 5,
      }),
    cancelSos: () =>
      set({
        sosActive: false,
        countdown: 5,
        sosPrefillLocation: null,
      }),
    completeSos: (payload = {}) =>
      set({
        sosActive: false,
        smsSent: Boolean(payload.smsSent),
        sosSessionId: payload.sosSessionId ?? null,
        sosPrefillLocation: null,
      }),
    setSosActive: (sosActive) => set({ sosActive }),
    setCountdown: (countdown) => set({ countdown }),
    setSosPrefillLocation: (sosPrefillLocation) => set({ sosPrefillLocation }),
  };
}

function createNearbySlice(set, get) {
  return {
    places: [],
    isLoading: false,
    lastFetched: null,
    fromCache: false,
    offlineIncidents: [],
    selectedPlace: null,
    setNearbyLoading: (isLoading) => set({ isLoading }),
    setPlaces: (places, options = {}) =>
      set({
        places,
        nearbyPlaces: places,
        fromCache: Boolean(options.fromCache),
        lastFetched: options.lastFetched ?? Date.now(),
      }),
    setNearbyPlaces: (nearbyPlaces) => set({ places: nearbyPlaces, nearbyPlaces }),
    setFromCache: (fromCache) => set({ fromCache }),
    setLastFetched: (lastFetched) => set({ lastFetched }),
    setOfflineIncidents: (offlineIncidents) => set({ offlineIncidents }),
    setSelectedPlace: (selectedPlace) => set({ selectedPlace }),
    loadOfflineCache: () => {
      const state = get();
      const key = `sos_cache_${geohash5(state.lat, state.lng)}`;
      const raw = localStorage.getItem(key);
      if (!raw) {
        set({ offlineIncidents: DEFAULT_OFFLINE_INCIDENTS });
        return;
      }

      try {
        const parsed = JSON.parse(raw);
        const cachedResults = Array.isArray(parsed.results) ? parsed.results : parsed;
        if (!Array.isArray(cachedResults) || !cachedResults.length) {
          set({ offlineIncidents: DEFAULT_OFFLINE_INCIDENTS });
          return;
        }
        const incidents = cachedResults.map((item, index) => ({
          id: item.id || index + 1,
          type: item.place_type || 'incident',
          name: item.name || 'Cached Incident',
          location: item.address || `${item.latitude?.toFixed?.(4) || '--'}, ${item.longitude?.toFixed?.(4) || '--'}`,
          unit: item.source ? String(item.source).toUpperCase() : 'CACHE',
          eta: item.distance_km != null ? `${Math.max(1, Math.round(item.distance_km * 3))}m` : null,
          status: 'CACHED',
          timestamp: new Date().toLocaleTimeString(),
        }));
        set({ offlineIncidents: incidents });
      } catch {
        set({ offlineIncidents: DEFAULT_OFFLINE_INCIDENTS });
      }
    },
  };
}

function createUiSlice(set, get) {
  return {
    onlineStatus: typeof navigator !== 'undefined' ? navigator.onLine : true,
    offlineMode: false,
    activeScreen: 'dashboard',
    toasts: [],
    toast: null,
    setOnlineStatus: (onlineStatus) => set({ onlineStatus }),
    setOfflineMode: (offlineMode) => set({ offlineMode }),
    setActiveScreen: (activeScreen) => set({ activeScreen }),
    addToast: (toastInput) => {
      const toast = typeof toastInput === 'string'
        ? { id: `${Date.now()}`, message: toastInput, type: 'info' }
        : {
            id: toastInput.id || `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
            message: toastInput.message,
            type: toastInput.type || 'info',
          };
      const nextToasts = [toast, ...get().toasts].slice(0, MAX_TOASTS);
      set({
        toasts: nextToasts,
        toast: nextToasts[0] || null,
      });
      return toast.id;
    },
    removeToast: (toastId) => {
      const nextToasts = get().toasts.filter((toast) => toast.id !== toastId);
      set({ toasts: nextToasts, toast: nextToasts[0] || null });
    },
    setToast: (message, type = 'info') => {
      const id = get().addToast({ message, type });
      setTimeout(() => {
        const hasToast = get().toasts.some((toast) => toast.id === id);
        if (hasToast) {
          get().removeToast(id);
        }
      }, 4000);
    },
    clearToast: () => {
      const current = get().toast;
      if (!current) {
        return;
      }
      get().removeToast(current.id);
    },
  };
}

function createTriageSlice(set) {
  return {
    sessionId: null,
    messages: [],
    currentIntent: null,
    currentSlots: {},
    followUpQuestion: null,
    currentTriageLevel: null,
    capAlert: null,
    addTriageMessage: (message) =>
      set((state) => ({
        messages: [...state.messages, message],
      })),
    setTriageSessionId: (sessionId) => set({ sessionId }),
    setTriageResult: (result) =>
      set({
        currentIntent: result.intent ?? null,
        currentSlots: result.slots ?? {},
        followUpQuestion: result.follow_up_question ?? null,
        currentTriageLevel: result.triage ?? result.triage_level ?? null,
        sessionId: result.session_id ?? null,
        capAlert: result.cap_alert ?? null,
      }),
    clearTriage: () =>
      set({
        sessionId: null,
        messages: [],
        currentIntent: null,
        currentSlots: {},
        followUpQuestion: null,
        currentTriageLevel: null,
        capAlert: null,
      }),
  };
}

export const useSosStore = create((set, get) => ({
  userLocation: { lat: 19.076, lng: 72.8777 },
  nearbyPlaces: [],
  activeSession: null,
  ...createLocationSlice(set, get),
  ...createSosSlice(set, get),
  ...createNearbySlice(set, get),
  ...createUiSlice(set, get),
  ...createTriageSlice(set, get),
  setActiveSession: (activeSession) => set({ activeSession }),
}));
