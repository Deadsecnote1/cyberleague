import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Users } from './pages/Users';
import { Activity } from './pages/Activity';
import { Workflows } from './pages/Workflows';
import { Settings } from './pages/Settings';
import { Broadcast } from './pages/Broadcast';
import { isAdminLoggedIn } from './lib/auth';

import type { ReactNode } from 'react';

function RequireAdmin({ children }: { children: ReactNode }) {
  if (!isAdminLoggedIn()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <RequireAdmin>
              <Layout />
            </RequireAdmin>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="users" element={<Users />} />
          <Route path="activity" element={<Activity />} />
          <Route path="workflows" element={<Workflows />} />
          <Route path="settings" element={<Settings />} />
          <Route path="broadcast" element={<Broadcast />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
