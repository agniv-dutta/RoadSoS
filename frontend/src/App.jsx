import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import SosModal from './components/SosModal';
import Toast from './components/Toast';
import { registerConnectivityListeners } from './utils/offlineCache';
import { getLocation, watchLocation } from './utils/geo';
import { useSosStore } from './store';

export default function App() {
  useEffect(() => {
    const teardownConnectivity = registerConnectivityListeners();
    const stopWatchingLocation = watchLocation();

    getLocation().catch(() => {
      const state = useSosStore.getState();
      if (!state.locationError) {
        state.setLocationError('Unable to fetch current location');
      }
    });

    return () => {
      teardownConnectivity();
      stopWatchingLocation();
    };
  }, []);

  return (
    <ErrorBoundary>
      <BrowserRouter>
        {/* Global UI Components */}
        <Toast />
        <SosModal />

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
