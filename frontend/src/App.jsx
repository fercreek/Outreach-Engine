import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import { ToastProvider } from './components/Toast';
import Dashboard from './pages/Dashboard';
import LeadCenter from './pages/LeadCenter';
import Templates from './pages/Templates';
import Dispatch from './pages/Dispatch';
import ActivityLog from './pages/ActivityLog';
import BlacklistPage from './pages/BlacklistPage';

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <div className="app-layout">
          <Sidebar />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/leads" element={<LeadCenter />} />
              <Route path="/templates" element={<Templates />} />
              <Route path="/dispatch" element={<Dispatch />} />
              <Route path="/logs" element={<ActivityLog />} />
              <Route path="/blacklist" element={<BlacklistPage />} />
            </Routes>
          </main>
        </div>
      </ToastProvider>
    </BrowserRouter>
  );
}
