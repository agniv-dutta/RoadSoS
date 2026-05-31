import { useSosStore } from '../store';
import { DEMO_COORDS, isDemoMode } from './demoData';

const BASE32 = '0123456789bcdefghjkmnpqrstuvwxyz';

function onLocationPermissionDenied() {
  const store = useSosStore.getState();
  store.setLocationError('Location access needed for emergency features');
  store.setToast('Location access needed for emergency features', 'error');
}

export function computeGeohash5(lat, lng) {
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

export function formatCoords(lat, lng) {
  const latAbs = Math.abs(lat).toFixed(4);
  const lngAbs = Math.abs(lng).toFixed(4);
  const latDir = lat >= 0 ? 'N' : 'S';
  const lngDir = lng >= 0 ? 'E' : 'W';
  return `${latAbs}° ${latDir}, ${lngAbs}° ${lngDir}`;
}

export function metersBetween(lat1, lng1, lat2, lng2) {
  const earthRadiusMeters = 6371000;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return earthRadiusMeters * c;
}

export function getLocation() {
  const store = useSosStore.getState();
  store.setIsLocating(true);

  if (isDemoMode()) {
    store.setLocation(DEMO_COORDS.lat, DEMO_COORDS.lng, 5);
    store.setIsLocating(false);
    return Promise.resolve({ lat: DEMO_COORDS.lat, lng: DEMO_COORDS.lng });
  }

  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      // Geolocation not supported — use IP fallback
      getLocationFromIP().then((ipLoc) => {
        store.setIsLocating(false);
        if (ipLoc) {
          store.setLocation(ipLoc.lat, ipLoc.lng, ipLoc.accuracy ?? null, 'ip');
          resolve(ipLoc);
        } else {
          // demo fallback
          store.setLocation(DEMO_COORDS.lat, DEMO_COORDS.lng, 5, 'demo');
          store.setIsLocating(false);
          resolve({ lat: DEMO_COORDS.lat, lng: DEMO_COORDS.lng, source: 'demo' });
        }
      });
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        const accuracy = position.coords.accuracy ?? null;
        store.setLocation(lat, lng, accuracy, 'gps');
        store.setIsLocating(false);
        resolve({ lat, lng, accuracy, source: 'gps' });
      },
      async (error) => {
        console.warn('GPS denied or failed:', error.message);
        // Fallback 1: try IP geolocation (Geoapify IP Geolocation API)
        const ipLoc = await getLocationFromIP();
        store.setIsLocating(false);
        if (ipLoc) {
          store.setLocation(ipLoc.lat, ipLoc.lng, ipLoc.accuracy ?? null, 'ip');
          resolve({ ...ipLoc, source: 'ip' });
        } else {
          // Fallback 2: default to Mumbai for demo
          console.warn('Using demo location: Mumbai');
          store.setLocation(DEMO_COORDS.lat, DEMO_COORDS.lng, 5, 'demo');
          resolve({ lat: DEMO_COORDS.lat, lng: DEMO_COORDS.lng, source: 'demo' });
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000, // 5 min cache — prevents repeated permission dialogs
      }
    );
  });
}

async function getLocationFromIP() {
  try {
    const key = import.meta.env.VITE_GEOAPIFY_KEY || '';
    const res = await fetch(
      `https://api.geoapify.com/v1/ipinfo?apiKey=${key}`,
      { signal: typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function' ? AbortSignal.timeout(5000) : undefined }
    );
    if (!res.ok) return null;
    const data = await res.json();
    return {
      lat: data.location?.latitude,
      lng: data.location?.longitude,
      city: data.city?.name,
      accuracy: null,
      source: 'ip',
    };
  } catch {
    return null;
  }
}

export function watchLocation(callback) {
  if (isDemoMode()) {
    const store = useSosStore.getState();
    const next = { lat: DEMO_COORDS.lat, lng: DEMO_COORDS.lng, accuracy: 5 };
    store.setLocation(next.lat, next.lng, next.accuracy);
    if (typeof callback === 'function') {
      callback(next);
    }
    return () => {};
  }

  if (!navigator.geolocation) {
    return () => {};
  }

  const store = useSosStore.getState();
  let debounceTimer = null;

  const watchId = navigator.geolocation.watchPosition(
    (position) => {
      const next = {
        lat: position.coords.latitude,
        lng: position.coords.longitude,
        accuracy: position.coords.accuracy ?? null,
      };

      if (debounceTimer) {
        clearTimeout(debounceTimer);
      }

      debounceTimer = setTimeout(() => {
        store.setLocation(next.lat, next.lng, next.accuracy);
        if (typeof callback === 'function') {
          callback(next);
        }
      }, 5000);
    },
    (error) => {
      if (error.code === error.PERMISSION_DENIED) {
        onLocationPermissionDenied();
      } else {
        store.setLocationError(error.message || 'Unable to monitor location');
      }
    },
    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
    }
  );

  return () => {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    navigator.geolocation.clearWatch(watchId);
  };
}
