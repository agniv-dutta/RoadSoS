const DEFAULT_API_URL = 'http://localhost:8000';

export function getApiBaseUrl() {
  return (import.meta.env.VITE_API_URL || DEFAULT_API_URL).replace(/\/$/, '');
}

function createTimeoutSignal(timeoutMs) {
  if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
    return AbortSignal.timeout(timeoutMs);
  }

  const controller = new AbortController();
  setTimeout(() => controller.abort(), timeoutMs);
  return controller.signal;
}

export async function checkBackendHealth(timeoutMs = 3000) {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/health`, {
      method: 'GET',
      signal: createTimeoutSignal(timeoutMs),
    });
    return response.ok;
  } catch {
    return false;
  }
}