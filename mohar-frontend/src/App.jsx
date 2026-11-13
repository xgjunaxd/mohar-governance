import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { RoleProvider, useRole } from './context/RoleContext';
import { checkBackendHealth } from './services/api';
import Navbar from './components/Navbar';
import Workspace from './pages/Workspace';
import Submit from './pages/Submit';
import Findings from './pages/Findings';
import Queue from './pages/Queue';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Knowledge from './pages/Knowledge';
import NotFound from './pages/NotFound';
import Toaster from './components/Toaster';

function MainLayout() {
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const { currentRole } = useRole();

  useEffect(() => {
    checkBackendHealth().then(setIsBackendOnline);
    const interval = setInterval(() => {
      checkBackendHealth().then(setIsBackendOnline);
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  // Signed out: the full-screen sign-in page (it has its own navigation).
  if (!currentRole) {
    return (
      <>
        <Toaster />
        <Login />
      </>
    );
  }

  return (
    <div className="min-h-screen flex flex-col font-sans">
      <Navbar isBackendOnline={isBackendOnline} />
      <Toaster />
      <div className="flex-grow">
        <Routes>
          <Route path="/" element={<Workspace />} />
          <Route path="/submit" element={<Submit />} />
          <Route path="/findings/:id" element={<Findings />} />
          <Route path="/queue" element={<Queue />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/knowledge" element={<Knowledge />} />
          <Route path="/login" element={<Navigate to="/" replace />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </div>
      <footer className="border-t py-4 text-center text-xs">
        Mohar Brand Governance Platform • AstraPay Demo Workspace • CodeNexus India 2026
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <RoleProvider>
      <BrowserRouter>
        <MainLayout />
      </BrowserRouter>
    </RoleProvider>
  );
}
