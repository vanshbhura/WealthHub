import React from 'react';
import { useNavigate } from 'react-router-dom';
import Greeting from '../components/Greeting';
import TotalWealthHero from '../components/TotalWealthHero';
import WealthGraph from '../components/WealthGraph';
import InvestmentGrid from '../components/InvestmentGrid';
import RecentActivity from '../components/RecentActivity';
import AddPlatformModal from '../components/AddPlatformModal';
import StatementImportModal from '../components/StatementImportModal';

export default function DashboardPage({
  currentUser,
  summary,
  displayedPlatforms,
  snapshotsData,
  activeTimeframe,
  isLoadingPortfolio,
  portfolioError,
  loadPortfolioData,
  handleTimeframeChange,
  isAddModalOpen,
  setIsAddModalOpen,
  isStatementModalOpen,
  setIsStatementModalOpen,
  targetPlatformForImport,
  setTargetPlatformForImport,
  handleDirectConnect,
  handleImportComplete,
}) {
  const navigate = useNavigate();

  // Determine current total, day change, day change percentage
  const isLive = Boolean(currentUser && summary);
  const currentTotal = isLive ? summary.total_wealth : displayedPlatforms.reduce((acc, p) => acc + (p.current_value || p.currentValue || 0), 0);
  const dayChange = isLive ? summary.today_change : displayedPlatforms.reduce((acc, p) => acc + (p.today_change || p.dayChange || 0), 0);
  const dayChangePercent = isLive ? summary.today_change_percentage : (currentTotal > 0 ? (dayChange / currentTotal) * 100 : null);

  const handleSelectPlatform = (platform) => {
    const id = platform.platform_id || platform.id || platform.platform_slug;
    navigate(`/platforms/${id}`);
  };

  return (
    <div className="dashboard-content">
      {/* 1. GREETING */}
      <Greeting userName={currentUser ? currentUser.full_name.split(' ')[0] : 'Aditya'} />

      {/* 2 & 3. TOTAL WEALTH HERO & SECONDARY METRICS ROW */}
      <TotalWealthHero
        currentTotal={currentTotal}
        dayChange={dayChange}
        dayChangePercent={dayChangePercent}
        investedAmount={summary?.invested_amount}
        totalProfitLoss={summary?.total_profit_loss}
        totalReturnPercentage={summary?.total_return_percentage}
        isLoading={isLoadingPortfolio}
        onConnectFirst={() => setIsAddModalOpen(true)}
      />

      {/* 4. WEALTH GRAPH (1M, 2M, 6M, 12M, 24M, 5Y) */}
      <WealthGraph
        currentTotal={currentTotal}
        snapshots={snapshotsData.snapshots}
        hasSufficientHistory={snapshotsData.has_sufficient_history}
        activeTimeframe={activeTimeframe}
        onTimeframeChange={handleTimeframeChange}
        isLoading={isLoadingPortfolio}
      />

      {/* 5 & 6. YOUR INVESTMENTS & + ADD PLATFORM CARD */}
      <InvestmentGrid
        platforms={displayedPlatforms}
        onSelectPlatform={handleSelectPlatform}
        onOpenAddPlatform={() => setIsAddModalOpen(true)}
        onRetry={() => loadPortfolioData(activeTimeframe)}
        isLoading={isLoadingPortfolio}
        isError={Boolean(portfolioError)}
      />

      {/* 7. RECENT ACTIVITY */}
      <RecentActivity platforms={displayedPlatforms} />

      {/* MODAL: ADD PLATFORM */}
      <AddPlatformModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        connectedPlatformIds={displayedPlatforms.map(p => p.id || p.platform_id)}
        onDirectConnect={handleDirectConnect}
        onOpenStatementImport={(platform) => {
          setTargetPlatformForImport(platform);
          setIsAddModalOpen(false);
          setIsStatementModalOpen(true);
        }}
      />

      {/* MODAL: STATEMENT IMPORT */}
      <StatementImportModal
        isOpen={isStatementModalOpen}
        onClose={() => {
          setIsStatementModalOpen(false);
          setTargetPlatformForImport(null);
        }}
        targetPlatform={targetPlatformForImport}
        onImportComplete={handleImportComplete}
      />
    </div>
  );
}
