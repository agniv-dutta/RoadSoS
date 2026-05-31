import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import SosModal from './components/SosModal';
import Toast from './components/Toast';

export default function App() {
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
