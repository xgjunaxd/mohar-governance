import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { RoleProvider } from './context/RoleContext';
import { checkBackendHealth } from './services/api';
import Navbar from './components/Navbar';
import Workspace from './pages/Workspace';
import Submit from './pages/Submit';
import Findings from './pages/Findings';
import Queue from './pages/Queue';
import Dashboard from './pages/Dashboard';

function MainLayout() {
  const [isBackendOnline, setIsBackendOnline] = useState(false);

  useEffect(() => {
    checkBackendHealth().then(setIsBackendOnline);
    const interval = setInterval(() => {
      checkBackendHealth().then(setIsBackendOnline);
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar isBackendOnline={isBackendOnline} />
      <main className="flex-grow">
        <Routes>
          <Route path="/" element={<Workspace />} />
          <Route path="/submit" element={<Submit />} />
          <Route path="/findings/:id" element={<Findings />} />
          <Route path="/queue" element={<Queue />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500">
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
