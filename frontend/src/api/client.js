import axios from 'axios';
import { useSosStore } from '../store/useSosStore';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 10000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // If backend is down or network fails
    if (!error.response || error.code === 'ERR_NETWORK') {
      useSosStore.getState().setToast('Backend unavailable — operating in offline mode', 'error');
      // If we go offline in application level
      useSosStore.getState().setOnlineStatus(false);
    } else {
      const message = error.response?.data?.detail || 'An error occurred during communication';
      useSosStore.getState().setToast(message, 'error');
    }
    return Promise.reject(error);
  }
);

export const api = {
  getNearby: async (lat, lng, radius_km = 10) => {
    try {
      const response = await apiClient.get('/api/nearby', {
        params: { lat, lng, radius_km }
      });
      return response.data;
    } catch (err) {
      // Caught by interceptor, but we throw or return mock data to prevent white screen
      return { results: [], count: 0, cached: false };
    }
  },

  getPlaceDetail: async (id, lat, lng) => {
    try {
      const response = await apiClient.get(`/api/nearby/${id}`, {
        params: lat && lng ? { lat, lng } : {}
      });
      return response.data;
    } catch (err) {
      return null;
    }
  },

  sendSos: async (lat, lng, phone = null) => {
    try {
      const response = await apiClient.post('/api/sos', {
        latitude: lat,
        longitude: lng,
        phone
      });
      return response.data;
    } catch (err) {
      // Build a fallback response if backend is offline
      const googleMapsLink = `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
      const whatsappMsg = encodeURIComponent(`Emergency alert! Coordinates: ${lat.toFixed(4)}, ${lng.toFixed(4)}. Location: ${googleMapsLink}`);
      return {
        sos_id: Date.now(),
        nearest_hospital: null,
        google_maps_link: googleMapsLink,
        whatsapp_link: `https://wa.me/?text=${whatsappMsg}`,
        sms_sent: false,
        is_fallback: true
      };
    }
  },

  submitTriage: async (message, sessionId = '') => {
    try {
      const response = await apiClient.post('/api/triage', {
        message,
        session_id: sessionId
      });
      return response.data;
    } catch (err) {
      return null;
    }
  },

  parseTriageMessage: async (text, sessionId = null, languageHint = null) => {
    try {
      const response = await apiClient.post('/api/triage/parse-message', {
        text,
        session_id: sessionId,
        language_hint: languageHint
      });
      return response.data;
    } catch (err) {
      return null;
    }
  }
};
