const BACKEND_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export async function checkBackendHealth(retries = 3) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const controller = new AbortController();
      // Give Render 25s to wake up on first attempt, 5s after
      const timeout = attempt === 1 ? 25000 : 5000;
      const timer = setTimeout(() => controller.abort(), timeout);

      const res = await fetch(`${BACKEND_URL}/api/ping`, {
        method: 'GET',
        signal: controller.signal,
        headers: { 'Accept': 'application/json' },
        // No credentials — matches allow_credentials=False on backend
      });
      clearTimeout(timer);

      if (res.ok) {
        console.log(`✓ Backend online (attempt ${attempt})`);
        return true;
      }
    } catch (err) {
      console.warn(`Backend check attempt ${attempt} failed:`, err?.message || err);
      if (attempt < retries) {
        // Wait 3s between retries
        await new Promise((r) => setTimeout(r, 3000));
      }
    }
  }
  return false;
}