import axios from 'axios';
import {
  api,
  getNearby,
  postSOS,
  parseMessage,
  checkHealth,
  batchEvaluate,
  postFeedback,
} from './index';

const baseURL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const plainClient = axios.create({
  baseURL,
  timeout: 12000,
});

// Backward-compatible method names used by existing pages.
api.sendSos = postSOS;
api.parseTriageMessage = parseMessage;
api.getPlaceDetail = async (id, lat, lng) => {
  const response = await plainClient.get(`/api/nearby/${id}`, {
    params: lat && lng ? { lat, lng } : {},
  });
  return response.data;
};

export { api, getNearby, postSOS, parseMessage, checkHealth, batchEvaluate, postFeedback };
