import React, { useMemo } from 'react';
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

  // Determine current total, day change, day change percentage using single source of truth
  const isLive = Boolean(currentUser && summary);

  const activeSummary = useMemo(() => {
    if (isLive && summary) {
      return summary;
    }
    const totalWealth = displayedPlatforms.reduce((acc, p) => acc + (p.current_value || p.currentValue || 0), 0);
    const investedVal = displayedPlatforms.reduce((acc, p) => acc + (p.invested_value || p.investedValue || 0), 0);
    const pl = totalWealth - investedVal;
    const plPct = investedVal > 0 ? (pl / investedVal) * 100 : 0;
    const dayDelta = displayedPlatforms.reduce((acc, p) => acc + (p.today_change || p.dayChange || 0), 0);
    const dayDeltaPct = totalWealth > 0 ? (dayDelta / totalWealth) * 100 : null;
    const assetCnt = displayedPlatforms.reduce((acc, p) => acc + (p.holdings?.length || p.asset_count || 1), 0);

    return {
      total_wealth: totalWealth,
      invested_value: investedVal,
      profit_loss: pl,
      profit_loss_percentage: plPct,
      today_change: dayDelta,
      today_change_percentage: dayDeltaPct,
      asset_count: assetCnt,
      platform_count: displayedPlatforms.length,
    };
  }, [isLive, summary, displayedPlatforms]);

  const currentTotal = activeSummary.total_wealth;
  const dayChange = activeSummary.today_change;
  const dayChangePercent = activeSummary.today_change_percentage;

  const handleSelectPlatform = (platform) => {
    const id = platform.platform_id || platform.id || platform.platform_slug;
    navigate(`/platforms/${id}`);
  };

  return (
    <div className="dashboard-content">
      {/* 1. GREETING */}
      <Greeting userName={currentUser ? currentUser.full_name.split(' ')[0] : 'Vansh'} />

      {/* 2 & 3. TOTAL WEALTH HERO & SECONDARY METRICS ROW */}
      <TotalWealthHero
        summary={activeSummary}
        currentTotal={currentTotal}
        dayChange={dayChange}
        dayChangePercent={dayChangePercent}
        investedAmount={activeSummary.invested_value}
        totalProfitLoss={activeSummary.profit_loss}
        totalReturnPercentage={activeSummary.profit_loss_percentage}
        isLoading={isLoadingPortfolio}
        isError={Boolean(portfolioError)}
        errorMessage={portfolioError}
        onRetry={() => loadPortfolioData(activeTimeframe)}
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
