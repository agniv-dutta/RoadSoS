import axios from 'axios';
import { useSosStore } from '../store';
import { loadNearbyCache, saveNearbyCache } from '../utils/offlineCache';

const DEFAULT_API_URL = 'http://localhost:8000';
const API_BASE_URL = (import.meta.env.VITE_API_URL || DEFAULT_API_URL).replace(/\/$/, '');

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 12000,
});

function buildStructuredError(error) {
  if (error?.isStructuredError) {
    return error;
  }

  const code =
    error?.response?.status?.toString() ||
    error?.code ||
    'UNKNOWN_ERROR';
  const detail = error?.response?.data?.detail || error?.message || 'Request failed';
  const message =
    error?.response?.data?.message ||
    (typeof detail === 'string' ? detail : 'Request failed');

  const structured = {
    code,
    message,
    detail,
    isStructuredError: true,
  };

  return structured;
}

apiClient.interceptors.request.use((config) => {
  const state = useSosStore.getState();
  const sessionId = state.sessionId || state.sosSessionId;
  if (sessionId) {
    config.headers['X-Session-ID'] = sessionId;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    const state = useSosStore.getState();
    state.setOfflineMode(false);
    state.setOnlineStatus(true);
    return response;
  },
  async (error) => {
    const networkError = !error.response || error.code === 'ERR_NETWORK';
    if (networkError) {
      const state = useSosStore.getState();
      state.setOfflineMode(true);
      state.setOnlineStatus(false);

      const fallbackFactory = error?.config?.metadata?.cacheFallback;
      if (typeof fallbackFactory === 'function') {
        const fallback = fallbackFactory();
        if (fallback) {
          return Promise.resolve({
            data: fallback,
            status: 200,
            statusText: 'CACHE_FALLBACK',
            headers: {},
            config: error.config,
          });
        }
      }
    }

    return Promise.reject(buildStructuredError(error));
  }
);

export async function getNearby(lat, lng, radiusKm = 10, type = 'all') {
  try {
    const response = await apiClient.get('/api/nearby', {
      params: {
        lat,
        lng,
        radius_km: radiusKm,
        type,
      },
      metadata: {
        cacheFallback: () => {
          const cached = loadNearbyCache(lat, lng);
          if (!cached) {
            return null;
          }
          return {
            results: cached.results,
            count: cached.results.length,
            center: { lat, lng },
            radius_km: radiusKm,
            cached: true,
            from_cache: true,
            cache_timestamp: cached.timestamp,
          };
        },
      },
    });

    if (Array.isArray(response.data?.results)) {
      saveNearbyCache(lat, lng, response.data.results);
    }

    return response.data;
  } catch (error) {
    throw buildStructuredError(error);
  }
}

export async function postSOS(lat, lng, phone = null) {
  try {
    const response = await apiClient.post('/api/sos', {
      latitude: lat,
      longitude: lng,
      phone,
    });
    return response.data;
  } catch (error) {
    throw buildStructuredError(error);
  }
}

export async function parseMessage(text, sessionId = null, languageHint = null) {
  try {
    const response = await apiClient.post('/api/triage/parse-message', {
      text,
      session_id: sessionId,
      language_hint: languageHint,
    });
    return response.data;
  } catch (error) {
    throw buildStructuredError(error);
  }
}

export async function checkHealth() {
  try {
    const response = await apiClient.get('/api/health');
    return response.data;
  } catch (primaryError) {
    try {
      const fallbackResponse = await apiClient.get('/health');
      return fallbackResponse.data;
    } catch {
      throw buildStructuredError(primaryError);
    }
  }
}

export async function batchEvaluate(messages) {
  try {
    const response = await apiClient.post('/api/triage/batch', messages);
    return response.data;
  } catch (error) {
    throw buildStructuredError(error);
  }
}

export async function postFeedback(placeId, issue, correctValue) {
  try {
    const response = await apiClient.post('/api/feedback', {
      place_id: placeId,
      issue,
      correct_value: correctValue,
    });
    return response.data;
  } catch (error) {
    throw buildStructuredError(error);
  }
}

export const api = {
  getNearby,
  postSOS,
  parseMessage,
  checkHealth,
  batchEvaluate,
  postFeedback,
};
