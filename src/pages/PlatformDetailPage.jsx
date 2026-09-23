import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Trash2, Plus, Check, AlertCircle, RotateCcw, UploadCloud } from 'lucide-react';
import PlatformLogo from '../components/PlatformLogo';
import HoldingsTable from '../components/HoldingsTable';
import TransactionsList from '../components/TransactionsList';
import ManualAssetModal from '../components/ManualAssetModal';
import StatementImportModal from '../components/StatementImportModal';
import GrowwConnectModal from '../components/GrowwConnectModal';
import { TableSkeleton } from '../components/Skeletons';
import { portfolioApi, transactionApi, authApi, connectionsApi } from '../api';
import { formatINR, formatPercent } from '../utils/formatters';

const STORAGE_KEY = 'wealthhub_connected_platforms_v1';

export default function PlatformDetailPage() {
  const { platformId } = useParams();
  const navigate = useNavigate();

  const [platform, setPlatform] = useState(null);
  const [connection, setConnection] = useState(null);
  const [holdings, setHoldings] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'holdings' | 'transactions'
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [syncNotice, setSyncNotice] = useState(null);
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isGrowwModalOpen, setIsGrowwModalOpen] = useState(false);
  const [showConfirmDisconnect, setShowConfirmDisconnect] = useState(false);

  // Load platform and connection data
  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const isAuth = authApi.isAuthenticated();

      if (isAuth) {
        // Fetch from live backend
        const [platformsRes, allAssetsRes, userConnsRes] = await Promise.all([
          portfolioApi.getConnectedPlatforms(),
          portfolioApi.getAssets().catch(() => []),
          connectionsApi.getConnections().catch(() => []),
        ]);

        const matched = platformsRes.find(
          p => String(p.platform_id) === String(platformId) || 
               String(p.id) === String(platformId) ||
               p.platform_slug === platformId
        );

        if (matched) {
          setPlatform(matched);

          // Match connection
          const matchedConn = userConnsRes.find(
            c => String(c.platform_id) === String(matched.platform_id || matched.id)
          );
          setConnection(matchedConn || null);

          // Filter holdings for this platform
          const platformAssets = allAssetsRes.filter(
            a => String(a.platform_id) === String(matched.platform_id || matched.id) ||
                 a.platform_name?.toLowerCase() === matched.platform_name?.toLowerCase()
          );
          setHoldings(platformAssets);

          // Fetch transactions for this platform
          try {
            const txRes = await transactionApi.getAll({
              platform_id: matched.platform_id || matched.id,
              limit: 50
            });
            setTransactions(txRes || []);
          } catch (e) {
            console.error('Error fetching transactions:', e);
            setTransactions([]);
          }
        } else {
          setPlatform(null);
        }
      } else {
        // Fallback to local storage
        const saved = localStorage.getItem(STORAGE_KEY);
        const platformsList = saved ? JSON.parse(saved) : [];
        const matched = platformsList.find(
          p => String(p.id) === String(platformId) || p.name?.toLowerCase() === platformId?.toLowerCase()
        );

        if (matched) {
          setPlatform(matched);
          setHoldings(matched.holdings || []);
          setTransactions(matched.transactions || []);
        } else {
          setPlatform(null);
        }
      }
    } catch (err) {
      console.error('Error loading platform detail:', err);
    } finally {
      setIsLoading(false);
    }
  }, [platformId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle Sync / Refresh
  const handleRefresh = async () => {
    setIsRefreshing(true);
    setSyncNotice(null);
    try {
      if (authApi.isAuthenticated() && connection) {
        const syncRes = await connectionsApi.syncConnection(connection.id);
        if (syncRes.status === 'SUCCESS') {
          setSyncNotice({ type: 'success', text: `Sync complete: ${syncRes.records_processed} records verified.` });
        } else {
          setSyncNotice({ type: 'error', text: syncRes.safe_error_message || 'Sync failed.' });
        }
      }
      await loadData();
    } catch (e) {
      console.error('Error syncing connection:', e);
      setSyncNotice({ type: 'info', text: 'Portfolio refreshed.' });
    } finally {
      setIsRefreshing(false);
      setTimeout(() => setSyncNotice(null), 5000);
    }
  };

  // Handle Reconnect
  const handleReconnect = async () => {
    if (!platform) return;
    try {
      if (authApi.isAuthenticated()) {
        await connectionsApi.createConnection({
          platform_id: platform.platform_id || platform.id,
          connection_type: 'MANUAL',
          connector_key: 'manual_asset'
        });
      }
      await loadData();
    } catch (e) {
      console.error('Error reconnecting platform:', e);
    }
  };

  // Handle Disconnect
  const handleDisconnect = async () => {
    try {
      if (authApi.isAuthenticated() && connection) {
        await connectionsApi.disconnectConnection(connection.id, false);
      } else {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
          const list = JSON.parse(saved).filter(p => String(p.id) !== String(platformId));
          localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
        }
      }
    } catch (e) {
      console.error('Error disconnecting platform:', e);
    }
    navigate('/');
  };

  if (isLoading) {
    return (
      <div className="platform-detail-container" style={{ padding: '28px 0' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <div className="skeleton-bar" style={{ width: 100, height: 28 }} />
        </div>
        <div className="skeleton-bar" style={{ width: '100%', height: 160, marginBottom: 24 }} />
        <TableSkeleton rows={4} />
      </div>
    );
  }

  if (!platform) {
    return (
      <div className="platform-detail-container" style={{ padding: '48px 0', textAlign: 'center' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: 12 }}>Platform not found</h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>
          The requested investment platform could not be located in your connected accounts.
        </p>
        <Link to="/" className="btn-primary" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 16px' }}>
          <ArrowLeft size={14} /> Back to Dashboard
        </Link>
      </div>
    );
  }

  const name = platform.platform_name || platform.name || 'Platform';
  const category = platform.category || platform.tagline || 'Investment';
  const currentValue = platform.current_value !== undefined ? platform.current_value : (platform.currentValue || 0);
  const investedValue = platform.invested_amount !== undefined ? platform.invested_amount : (platform.investedValue || 0);
  const profitLoss = platform.profit_loss !== undefined ? platform.profit_loss : (platform.profitLoss || (currentValue - investedValue));
  const returnPct = platform.profit_loss_percentage !== undefined 
    ? platform.profit_loss_percentage 
    : (platform.returnPercentage || (investedValue > 0 ? ((currentValue - investedValue) / investedValue) * 100 : null));
  const todayChange = platform.today_change;
  const todayChangePct = platform.today_change_percentage;

  const status = (connection?.status || platform.status || 'CONNECTED').toLowerCase();
  const isDisconnected = status === 'disconnected';
  const isDirectApi = connection?.connection_type === 'DIRECT_API' || connection?.connector_key === 'groww_direct';
  const isAuthRequired = status === 'auth_required' || status === 'token_expired';
  const isImported = connection?.connection_type === 'IMPORT' || platform.integration_type === 'STATEMENT_IMPORT' || status === 'imported';

  const displayStatus = isDisconnected
    ? 'Disconnected'
    : isAuthRequired
    ? 'Auth Required'
    : isDirectApi
    ? (status === 'synced' || status === 'connected' ? 'Connected' : status.toUpperCase())
    : isImported
    ? 'Imported'
    : status === 'synced' || status === 'connected'
    ? 'Connected'
    : status === 'awaiting'
    ? 'Awaiting'
    : 'Manual';

  const connectionMethod = isDirectApi
    ? 'Live API'
    : isImported
    ? 'Imported Statement'
    : connection?.connection_type 
    ? connection.connection_type.replace(/_/g, ' ') 
    : (platform.integration_method || 'Manual');

  return (
    <div className="platform-detail-container">
      {/* Back Link & Detail Actions */}
      <div className="detail-nav-bar">
        <Link to="/" className="back-link">
          <ArrowLeft size={15} />
          <span>Back to Dashboard</span>
        </Link>
        <div className="detail-actions">
          {isDisconnected || isAuthRequired ? (
            <button
              className="icon-btn"
              onClick={() => isDirectApi ? setIsGrowwModalOpen(true) : handleReconnect()}
              title="Reconnect platform"
              style={{ color: 'var(--positive, #059669)' }}
            >
              <RotateCcw size={13} />
              <span>Reconnect</span>
            </button>
          ) : (
            <>
              <button
                className="icon-btn"
                onClick={() => setIsImportModalOpen(true)}
                title="Import CSV, Excel, or PDF statement"
              >
                <UploadCloud size={13} />
                <span>Import Statement</span>
              </button>
              <button
                className="icon-btn"
                onClick={() => setIsManualModalOpen(true)}
                title="Add asset or holding to this platform"
              >
                <Plus size={13} />
                <span>Add Asset</span>
              </button>
              <button
                className="icon-btn"
                onClick={handleRefresh}
                title="Sync this platform"
                disabled={isRefreshing}
              >
                <RefreshCw size={13} className={isRefreshing ? 'spin-anim' : ''} />
                <span>{isRefreshing ? 'Syncing...' : 'Sync'}</span>
              </button>
              <button
                className="icon-btn danger"
                onClick={() => setShowConfirmDisconnect(true)}
                title="Disconnect platform"
              >
                <Trash2 size={13} />
                <span>Disconnect</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Sync Status Toast */}
      {syncNotice && (
        <div
          style={{
            padding: '10px 14px',
            marginBottom: 16,
            borderRadius: 6,
            background: syncNotice.type === 'error' ? 'rgba(239, 68, 68, 0.08)' : 'var(--bg-subtle)',
            border: `1px solid ${syncNotice.type === 'error' ? 'rgba(239, 68, 68, 0.2)' : 'var(--border-subtle)'}`,
            color: syncNotice.type === 'error' ? 'var(--negative)' : 'var(--text-primary)',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}
        >
          {syncNotice.type === 'error' ? <AlertCircle size={15} /> : <Check size={15} color="var(--positive)" />}
          <span>{syncNotice.text}</span>
        </div>
      )}

      {/* Confirmation Modal for Disconnect */}
      {showConfirmDisconnect && (
        <div className="modal-overlay" onClick={() => setShowConfirmDisconnect(false)}>
          <div className="modal-card" onClick={e => e.stopPropagation()} style={{ maxWidth: 420 }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 8 }}>Disconnect {name}?</h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: 20, lineHeight: 1.5 }}>
              Are you sure you want to disconnect {name}? The platform connection will be detached. Your historical financial records will be preserved safely.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button
                className="btn-secondary"
                onClick={() => setShowConfirmDisconnect(false)}
                style={{ padding: '7px 14px', borderRadius: 6 }}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleDisconnect}
                style={{ padding: '7px 14px', borderRadius: 6, background: 'var(--text-danger, #ef4444)', borderColor: 'transparent', color: '#fff' }}
              >
                Disconnect
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Platform Header Hero */}
      <div className="platform-detail-hero">
        <div className="detail-hero-top">
          <div className="detail-platform-info">
            <PlatformLogo platform={platform} size={48} fontSize="1.3rem" />
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <h1 className="detail-platform-name">{name}</h1>
                <span className={`status-badge ${isImported ? 'synced' : status === 'connected' || status === 'synced' ? 'synced' : status === 'awaiting' ? 'awaiting' : status === 'disconnected' ? 'manual' : 'manual'}`}>
                  {displayStatus}
                </span>
              </div>
              <span className="detail-platform-cat">{category}</span>
              {isImported && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 6, fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                  <span>Method: <strong style={{ color: 'var(--text-primary)' }}>Imported Statement</strong></span>
                  {connection?.last_synced_at && (
                    <span>Last Imported: <strong style={{ color: 'var(--text-primary)' }}>{new Date(connection.last_synced_at).toLocaleDateString()}</strong></span>
                  )}
                  {connection?.last_sync_status && (
                    <span>Status: <strong style={{ color: 'var(--positive)' }}>Successful</strong></span>
                  )}
                  <span>Records: <strong style={{ color: 'var(--text-primary)' }}>{transactions.length}</strong></span>
                </div>
              )}
              {isDirectApi && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 6, fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                  <span>Method: <strong style={{ color: 'var(--text-primary)' }}>Live API</strong></span>
                  {connection?.last_synced_at && (
                    <span>Last Synced: <strong style={{ color: 'var(--text-primary)' }}>{new Date(connection.last_synced_at).toLocaleString()}</strong></span>
                  )}
                  <span>Sync Status: <strong style={{ color: isAuthRequired ? 'var(--negative, #ef4444)' : 'var(--positive, #059669)' }}>{isAuthRequired ? 'Authentication Required' : 'Successful'}</strong></span>
                  <span>Holdings: <strong style={{ color: 'var(--text-primary)' }}>{holdings.length}</strong></span>
                </div>
              )}
              {isAuthRequired && isDirectApi && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 12,
                    marginTop: 10,
                    padding: '8px 12px',
                    borderRadius: 6,
                    background: 'rgba(239, 68, 68, 0.08)',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                    color: 'var(--danger, #dc2626)',
                    fontSize: '0.8rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <AlertCircle size={15} />
                    <span>Groww API access token has expired. Reconnect to resume live synchronization.</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsGrowwModalOpen(true)}
                    style={{
                      padding: '4px 10px',
                      borderRadius: 4,
                      background: 'var(--danger, #dc2626)',
                      color: '#ffffff',
                      border: 'none',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Reconnect Now
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="detail-primary-val">
            <span className="val-caption">CURRENT VALUE</span>
            <span className="val-amount">{formatINR(currentValue)}</span>
          </div>
        </div>

        {/* Value summary bar */}
        <div className="detail-metrics-grid">
          <div className="detail-metric-card">
            <span className="metric-caption">INVESTED AMOUNT</span>
            <span className="metric-value">{formatINR(investedValue)}</span>
          </div>

          <div className="detail-metric-card">
            <span className="metric-caption">TOTAL PROFIT / LOSS</span>
            <span className={`metric-value ${profitLoss >= 0 ? 'positive' : 'negative'}`}>
              {formatINR(profitLoss, { showSign: true })}
              {returnPct !== null && (
                <span className="metric-sub"> ({formatPercent(returnPct, true)})</span>
              )}
            </span>
          </div>

          <div className="detail-metric-card">
            <span className="metric-caption">TODAY'S CHANGE</span>
            {todayChange !== null && todayChange !== undefined ? (
              <span className={`metric-value ${todayChange >= 0 ? 'positive' : 'negative'}`}>
                {formatINR(todayChange, { showSign: true })}
                {todayChangePct !== null && todayChangePct !== undefined && (
                  <span className="metric-sub"> ({formatPercent(todayChangePct, true)})</span>
                )}
              </span>
            ) : (
              <span className="metric-value neutral">—</span>
            )}
          </div>

          <div className="detail-metric-card">
            <span className="metric-caption">HOLDINGS COUNT</span>
            <span className="metric-value">{holdings.length} Assets</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="detail-tabs-bar" role="tablist">
        <button
          role="tab"
          aria-selected={activeTab === 'overview'}
          className={`detail-tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'holdings'}
          className={`detail-tab-btn ${activeTab === 'holdings' ? 'active' : ''}`}
          onClick={() => setActiveTab('holdings')}
        >
          Holdings ({holdings.length})
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'transactions'}
          className={`detail-tab-btn ${activeTab === 'transactions' ? 'active' : ''}`}
          onClick={() => setActiveTab('transactions')}
        >
          Transactions ({transactions.length})
        </button>
      </div>

      {/* Tab Content */}
      <div className="detail-tab-content">
        {activeTab === 'overview' && (
          <div className="detail-overview-pane">
            <div className="overview-section">
              <h3 className="pane-section-title">Platform Connection Details</h3>
              <div className="info-key-value-list">
                <div className="kv-row">
                  <span className="kv-key">Connection Status</span>
                  <span className="kv-val" style={{ textTransform: 'capitalize' }}>
                    {isDisconnected ? 'Disconnected' : status}
                  </span>
                </div>
                <div className="kv-row">
                  <span className="kv-key">Connection Method</span>
                  <span className="kv-val" style={{ textTransform: 'capitalize' }}>
                    {connectionMethod}
                  </span>
                </div>
                <div className="kv-row">
                  <span className="kv-key">Last Synced</span>
                  <span className="kv-val">
                    {connection?.last_synced_at
                      ? new Date(connection.last_synced_at).toLocaleString('en-IN')
                      : platform.last_updated
                      ? new Date(platform.last_updated).toLocaleString('en-IN')
                      : 'Manual'}
                  </span>
                </div>
                <div className="kv-row">
                  <span className="kv-key">Last Sync Status</span>
                  <span className="kv-val">
                    {connection?.last_sync_status || (status === 'connected' ? 'Success' : '—')}
                  </span>
                </div>
              </div>
            </div>

            {holdings.length > 0 && (
              <div className="overview-section" style={{ marginTop: 24 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <h3 className="pane-section-title" style={{ margin: 0 }}>Top Holdings</h3>
                  <button
                    className="btn-text-link"
                    onClick={() => setActiveTab('holdings')}
                    style={{ background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: '0.85rem' }}
                  >
                    View all ({holdings.length}) →
                  </button>
                </div>
                <HoldingsTable assets={holdings.slice(0, 5)} />
              </div>
            )}
          </div>
        )}

        {activeTab === 'holdings' && (
          <div className="detail-holdings-pane">
            <HoldingsTable
              assets={holdings}
              onAddAsset={() => setIsManualModalOpen(true)}
            />
          </div>
        )}

        {activeTab === 'transactions' && (
          <div className="detail-transactions-pane">
            <TransactionsList transactions={transactions} />
          </div>
        )}
      </div>

      {/* Manual Asset Modal */}
      {isManualModalOpen && (
        <ManualAssetModal
          isOpen={isManualModalOpen}
          onClose={() => setIsManualModalOpen(false)}
          platform={platform}
          onAssetAdded={() => {
            loadData();
            setIsManualModalOpen(false);
          }}
        />
      )}

      {/* Statement Import Modal */}
      {isImportModalOpen && (
        <StatementImportModal
          isOpen={isImportModalOpen}
          onClose={() => setIsImportModalOpen(false)}
          targetPlatform={platform}
          onImportComplete={() => {
            loadData();
            setIsImportModalOpen(false);
          }}
        />
      )}

      {/* Groww Live API Connection / Reconnect Modal */}
      {isGrowwModalOpen && (
        <GrowwConnectModal
          isOpen={isGrowwModalOpen}
          onClose={() => setIsGrowwModalOpen(false)}
          platform={platform}
          onSuccess={() => {
            setIsGrowwModalOpen(false);
            loadData();
          }}
        />
      )}
    </div>
  );
}
