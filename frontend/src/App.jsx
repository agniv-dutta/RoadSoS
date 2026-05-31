import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import SosModal from './components/SosModal';
import Toast from './components/Toast';
import { registerConnectivityListeners } from './utils/offlineCache';
import { getLocation, watchLocation } from './utils/geo';
import { startKeepAlivePing } from './utils/keepAlive';
import { useSosStore, initConnectivity } from './store';

export default function App() {
  useEffect(() => {
    const teardownConnectivity = registerConnectivityListeners();
    const { startSos } = useSosStore.getState();
    // Run the initial connectivity check (handles cold-start tolerances)
    initConnectivity(useSosStore.setState).catch(() => {});
    const stopWatchingLocation = watchLocation();
    const stopKeepAlive = startKeepAlivePing();

    const handleEmergencyShortcut = (event) => {
      if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === 's') {
        event.preventDefault();
        startSos();
      }
    };

    window.addEventListener('keydown', handleEmergencyShortcut);

    getLocation().catch(() => {
      const state = useSosStore.getState();
      if (!state.locationError) {
        state.setLocationError('Unable to fetch current location');
      }
    });

    return () => {
      teardownConnectivity();
      // stopConnectivityMonitor is no longer used; connectivity interval is internal to initConnectivity
      stopWatchingLocation();
      stopKeepAlive();
      window.removeEventListener('keydown', handleEmergencyShortcut);
    };
  }, []);

  return (
    <ErrorBoundary>
      {/* Global UI Components must stay mounted above routing */}
      <Toast />
      <SosModal />
      <BrowserRouter>
        {/* Route Definitions */}
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/dashboard/place/:id" element={<Dashboard />} />
          
          {/* Fallback to Landing */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
