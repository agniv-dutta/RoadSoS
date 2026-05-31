import axios from 'axios';
import { useSosStore } from '../store';
import { computeGeohash5 } from './geo';

const CACHE_TTL_MS = 30 * 60 * 1000;
const PENDING_LOGS_KEY = 'sos_pending_logs';
let listenersAttached = false;

function getApiBaseUrl() {
  return (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
}

function getCacheKey(lat, lng) {
  return `sos_cache_${computeGeohash5(lat, lng)}`;
}

export function isStale(timestamp) {
  if (!timestamp) {
    return true;
  }
  return Date.now() - Number(timestamp) > CACHE_TTL_MS;
}

export function getCacheAge(timestamp) {
  if (!timestamp) {
    return 'unknown';
  }

  const deltaMs = Math.max(0, Date.now() - Number(timestamp));
  const mins = Math.floor(deltaMs / 60000);
  if (mins < 1) {
    return 'just now';
  }
  if (mins === 1) {
    return '1 min ago';
  }
  if (mins < 60) {
    return `${mins} mins ago`;
  }

  const hours = Math.floor(mins / 60);
  if (hours === 1) {
    return '1 hour ago';
  }
  return `${hours} hours ago`;
}

export function saveNearbyCache(lat, lng, results) {
  const key = getCacheKey(lat, lng);
  const payload = {
    timestamp: Date.now(),
    lat,
    lng,
    results: Array.isArray(results) ? results : [],
  };
  localStorage.setItem(key, JSON.stringify(payload));
  return payload;
}

export function loadNearbyCache(lat, lng) {
  try {
    const key = getCacheKey(lat, lng);
    const raw = localStorage.getItem(key);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw);
    if (!parsed.timestamp || isStale(parsed.timestamp)) {
      return null;
    }

    return parsed;
  } catch {
    return null;
  }
}

export function saveSosLog(sosData) {
  const existing = JSON.parse(localStorage.getItem(PENDING_LOGS_KEY) || '[]');
  const next = [
    ...existing,
    {
      ...sosData,
      createdAt: Date.now(),
    },
  ];
  localStorage.setItem(PENDING_LOGS_KEY, JSON.stringify(next));
  return next.length;
}

export async function syncPendingLogs() {
  if (!navigator.onLine) {
    return { synced: 0, remaining: JSON.parse(localStorage.getItem(PENDING_LOGS_KEY) || '[]').length };
  }

  const queue = JSON.parse(localStorage.getItem(PENDING_LOGS_KEY) || '[]');
  if (!queue.length) {
    return { synced: 0, remaining: 0 };
  }

  const api = axios.create({ baseURL: getApiBaseUrl(), timeout: 10000 });
  const pending = [];
  let synced = 0;

  for (const entry of queue) {
    try {
      await api.post('/api/sos', {
        latitude: entry.latitude,
        longitude: entry.longitude,
        phone: entry.phone || null,
      });
      synced += 1;
    } catch {
      pending.push(entry);
    }
  }

  localStorage.setItem(PENDING_LOGS_KEY, JSON.stringify(pending));
  return { synced, remaining: pending.length };
}

export function registerConnectivityListeners() {
  if (listenersAttached || typeof window === 'undefined') {
    return () => {};
  }
  listenersAttached = true;

  const handleOnline = async () => {
    const store = useSosStore.getState();
    const onlineStatus = await store.syncConnectivityStatus();
    if (!onlineStatus) {
      store.setToast('Network is back, but the backend is still unreachable.', 'error');
      return;
    }

    store.setToast('Connection restored. Syncing pending emergency logs.', 'success');
    const result = await syncPendingLogs();
    if (result.synced > 0) {
      store.setToast(`Synced ${result.synced} pending SOS logs`, 'success');
    }
  };

  const handleOffline = () => {
    const store = useSosStore.getState();
    store.setOfflineMode(true);
    store.setToast('Network connection dropped. Checking backend reachability in the background.', 'error');
  };

  window.addEventListener('online', handleOnline);
  window.addEventListener('offline', handleOffline);

  return () => {
    window.removeEventListener('online', handleOnline);
    window.removeEventListener('offline', handleOffline);
    listenersAttached = false;
  };
}
