const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const KEEP_ALIVE_INTERVAL_MS = 840000;

export function startKeepAlivePing() {
  const ping = () => {
    void fetch(`${BASE_URL}/api/health`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      mode: 'cors',
      cache: 'no-store',
      credentials: 'omit',
    }).catch(() => {});
  };

  ping();
  const intervalId = setInterval(ping, KEEP_ALIVE_INTERVAL_MS);

  return () => {
    clearInterval(intervalId);
  };
}