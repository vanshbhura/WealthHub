import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Header';
import DashboardPage from './pages/DashboardPage';
import PlatformDetailPage from './pages/PlatformDetailPage';
import AuthModal from './components/AuthModal';
import { initialPlatforms } from './data/initialPlatforms';
import { authApi } from './api/auth';
import { portfolioApi } from './api/portfolio';

const STORAGE_KEY = 'wealthhub_connected_platforms_v1';
const THEME_KEY = 'wealthhub_theme_v1';

export default function App() {
  // Theme state - defaults to 'light' per Prompt 4 design specifications
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem(THEME_KEY) || 'light';
  });

  // Auth state
  const [currentUser, setCurrentUser] = useState(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Backend Portfolio State
  const [summary, setSummary] = useState(null);
  const [backendPlatforms, setBackendPlatforms] = useState([]);
  const [snapshotsData, setSnapshotsData] = useState({ snapshots: [], has_sufficient_history: false });
  const [activeTimeframe, setActiveTimeframe] = useState('1M');
  const [isLoadingPortfolio, setIsLoadingPortfolio] = useState(false);
  const [portfolioError, setPortfolioError] = useState(null);

  // Local Platforms fallback for unauthenticated / demo state
  const [localPlatforms, setLocalPlatforms] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch (e) {
      console.error('Error loading saved platforms:', e);
    }
    return initialPlatforms;
  });

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isStatementModalOpen, setIsStatementModalOpen] = useState(false);
  const [targetPlatformForImport, setTargetPlatformForImport] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Apply theme to document element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  // Fetch live backend portfolio data
  const loadPortfolioData = useCallback(async (timeframe = activeTimeframe) => {
    if (!authApi.isAuthenticated()) return;
    setIsLoadingPortfolio(true);
    setPortfolioError(null);
    try {
      const [sumRes, platRes, snapRes] = await Promise.all([
        portfolioApi.getSummary(),
        portfolioApi.getConnectedPlatforms(),
        portfolioApi.getSnapshots(timeframe, true),
      ]);

      setSummary(sumRes);
      setBackendPlatforms(platRes);
      setSnapshotsData(snapRes || { snapshots: [], has_sufficient_history: false });
    } catch (err) {
      console.error('Error loading portfolio data:', err);
      setPortfolioError('Unable to load portfolio data.');
    } finally {
      setIsLoadingPortfolio(false);
    }
  }, [activeTimeframe]);

  // Check auth session on load
  useEffect(() => {
    if (authApi.isAuthenticated()) {
      authApi.getMe()
        .then(user => {
          setCurrentUser(user);
          loadPortfolioData(activeTimeframe);
        })
        .catch(() => {
          authApi.logout();
          setCurrentUser(null);
        });
    }
  }, [loadPortfolioData, activeTimeframe]);

  // Handle Timeframe filter change on historical graph
  const handleTimeframeChange = (tf) => {
    setActiveTimeframe(tf);
    if (currentUser) {
      portfolioApi.getSnapshots(tf, true)
        .then(res => setSnapshotsData(res || { snapshots: [], has_sufficient_history: false }))
        .catch(e => console.error('Error fetching snapshots for timeframe:', e));
    }
  };

  // Determine active displayed platforms
  const isLive = Boolean(currentUser && summary);
  const displayedPlatforms = isLive ? backendPlatforms : localPlatforms;

  // Handle Theme Toggle
  const handleToggleTheme = () => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Handle Sync All
  const handleRefreshAll = async () => {
    setIsRefreshing(true);
    if (currentUser) {
      await loadPortfolioData(activeTimeframe);
      setIsRefreshing(false);
    } else {
      setTimeout(() => {
        setLocalPlatforms(prev =>
          prev.map(p => ({
            ...p,
            lastUpdated: 'Updated just now',
            syncTimestamp: new Date().toISOString(),
          }))
        );
        setIsRefreshing(false);
      }, 800);
    }
  };

  // Handle Direct Connect
  const handleDirectConnect = async (catalogPlatform) => {
    setIsAddModalOpen(false);
    if (currentUser) {
      await loadPortfolioData(activeTimeframe);
    } else {
      const baseValue = Math.floor(65000 + Math.random() * 80000);
      const dayGain = Math.round(baseValue * 0.013);
      const newPlatform = {
        id: catalogPlatform.id,
        name: catalogPlatform.name,
        tagline: catalogPlatform.type,
        category: catalogPlatform.category,
        iconType: catalogPlatform.id,
        accentColor: catalogPlatform.accentColor || '#3b82f6',
        currentValue: baseValue,
        investedValue: Math.round(baseValue * 0.86),
        dayChange: dayGain,
        dayChangePercent: 1.3,
        status: 'synced',
        lastUpdated: 'Updated just now',
        syncTimestamp: new Date().toISOString(),
        integrationType: catalogPlatform.integrationLabel,
        xirr: 16.5,
        holdings: [],
        transactions: []
      };
      setLocalPlatforms(prev => [...prev.filter(p => p.id !== newPlatform.id), newPlatform]);
    }
  };

  // Handle Statement Import completion
  const handleImportComplete = (normalizedPlatform) => {
    if (currentUser) {
      loadPortfolioData(activeTimeframe);
    } else {
      setLocalPlatforms(prev => [...prev.filter(p => p.id !== normalizedPlatform.id), normalizedPlatform]);
    }
  };

  // Handle Auth Success
  const handleAuthSuccess = (user) => {
    setCurrentUser(user);
    loadPortfolioData(activeTimeframe);
  };

  // Handle Logout
  const handleLogout = () => {
    authApi.logout();
    setCurrentUser(null);
    setSummary(null);
    setBackendPlatforms([]);
    setSnapshotsData({ snapshots: [], has_sufficient_history: false });
  };

  return (
    <BrowserRouter>
      <div className="app-container">
        {/* Top Header */}
        <Header
          theme={theme}
          onToggleTheme={handleToggleTheme}
          onRefreshAll={handleRefreshAll}
          isRefreshing={isRefreshing}
          currentUser={currentUser}
          onOpenAuth={() => setIsAuthModalOpen(true)}
          onLogout={handleLogout}
        />

        {/* Routes */}
        <Routes>
          <Route
            path="/"
            element={
              <DashboardPage
                currentUser={currentUser}
                summary={summary}
                displayedPlatforms={displayedPlatforms}
                snapshotsData={snapshotsData}
                activeTimeframe={activeTimeframe}
                isLoadingPortfolio={isLoadingPortfolio}
                portfolioError={portfolioError}
                loadPortfolioData={loadPortfolioData}
                handleTimeframeChange={handleTimeframeChange}
                isAddModalOpen={isAddModalOpen}
                setIsAddModalOpen={setIsAddModalOpen}
                isStatementModalOpen={isStatementModalOpen}
                setIsStatementModalOpen={setIsStatementModalOpen}
                targetPlatformForImport={targetPlatformForImport}
                setTargetPlatformForImport={setTargetPlatformForImport}
                handleDirectConnect={handleDirectConnect}
                handleImportComplete={handleImportComplete}
              />
            }
          />
          <Route
            path="/platforms/:platformId"
            element={<PlatformDetailPage />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>

        {/* Global Auth Modal */}
        <AuthModal
          isOpen={isAuthModalOpen}
          onClose={() => setIsAuthModalOpen(false)}
          onAuthSuccess={handleAuthSuccess}
        />
      </div>
    </BrowserRouter>
  );
}
