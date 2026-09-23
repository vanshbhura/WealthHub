import React, { useState } from 'react';
import { X, RefreshCw, Trash2, ArrowUpRight, ArrowDownRight, CheckCircle2 } from 'lucide-react';
import { formatINR, formatPercent } from '../utils/formatters';

export default function PlatformDetailDrawer({
  platform,
  onClose,
  onDisconnect,
  onRefreshPlatform,
}) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState('holdings'); // 'holdings' | 'transactions'

  if (!platform) return null;

  const isPositiveDay = platform.dayChange >= 0;
  const totalGain = (platform.currentValue || 0) - (platform.investedValue || 0);
  const isPositiveTotal = totalGain >= 0;

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      onRefreshPlatform(platform.id);
      setIsRefreshing(false);
    }, 700);
  };

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <aside
        className="drawer-panel"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="platform-drawer-name"
      >
        {/* Drawer Header */}
        <div className="drawer-header">
          <div className="drawer-title-group">
            <div
              className="platform-badge-logo"
              style={{
                backgroundColor: platform.accentColor || '#3b82f6',
                width: 36,
                height: 36,
                fontSize: '1rem',
              }}
            >
              {platform.name.charAt(0)}
            </div>
            <div>
              <h2 id="platform-drawer-name" className="drawer-platform-name">
                {platform.name}
              </h2>
              <div className="drawer-platform-tag">{platform.tagline}</div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <button
              className="icon-btn"
              onClick={handleRefresh}
              disabled={isRefreshing}
              title="Refresh platform data"
            >
              <RefreshCw size={13} className={isRefreshing ? 'spin-anim' : ''} />
              <span>{isRefreshing ? 'Syncing...' : 'Sync'}</span>
            </button>
            <button
              className="modal-close-btn"
              onClick={onClose}
              aria-label="Close details"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Primary Value & Today's Movement */}
        <div style={{ marginBottom: 24 }}>
          <div className="wealth-label">PORTFOLIO VALUE</div>
          <div className="card-current-value" style={{ fontSize: '2.2rem', marginBottom: 6 }}>
            {formatINR(platform.currentValue)}
          </div>
          <div className={`card-change-line ${isPositiveDay ? 'positive' : 'negative'}`} style={{ fontSize: '0.95rem' }}>
            <span>{formatINR(platform.dayChange, { showSign: true })} today</span>
            <span>({formatPercent(platform.dayChangePercent, true)})</span>
          </div>
        </div>

        {/* Key Metrics Grid */}
        <div className="metric-cards-row">
          <div className="metric-tile">
            <div className="metric-tile-label">Total Invested</div>
            <div className="metric-tile-value">{formatINR(platform.investedValue)}</div>
          </div>

          <div className="metric-tile">
            <div className="metric-tile-label">Total Profit / Loss</div>
            <div
              className="metric-tile-value"
              style={{ color: isPositiveTotal ? 'var(--positive)' : 'var(--negative)' }}
            >
              {formatINR(totalGain, { showSign: true })}
            </div>
          </div>

          <div className="metric-tile">
            <div className="metric-tile-label">Overall Return %</div>
            <div
              className="metric-tile-value"
              style={{ color: isPositiveTotal ? 'var(--positive)' : 'var(--negative)' }}
            >
              {formatPercent(platform.gainPercent || (platform.investedValue ? (totalGain / platform.investedValue) * 100 : 0))}
            </div>
          </div>

          <div className="metric-tile">
            <div className="metric-tile-label">Annualized XIRR</div>
            <div className="metric-tile-value" style={{ color: 'var(--positive)' }}>
              {platform.xirr ? `${platform.xirr}%` : '—'}
            </div>
          </div>
        </div>

        {/* Freshness & Connection Status Bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--bg-subtle)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 14px',
            fontSize: '0.8rem',
            color: 'var(--text-secondary)',
            marginBottom: 24,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <CheckCircle2 size={14} color="var(--positive)" />
            <span>{platform.integrationType || 'Official Connected App'}</span>
          </div>
          <span style={{ color: 'var(--text-muted)' }}>{platform.lastUpdated}</span>
        </div>

        {/* Tabs: Holdings vs Transactions */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, borderBottom: '1px solid var(--border-subtle)' }}>
          <button
            type="button"
            className="time-btn"
            style={{
              padding: '6px 12px',
              fontSize: '0.85rem',
              fontWeight: activeTab === 'holdings' ? 600 : 400,
              color: activeTab === 'holdings' ? 'var(--text-primary)' : 'var(--text-muted)',
              borderBottom: activeTab === 'holdings' ? '2px solid var(--text-primary)' : 'none',
              borderRadius: 0,
            }}
            onClick={() => setActiveTab('holdings')}
          >
            Holdings ({platform.holdings?.length || 0})
          </button>
          <button
            type="button"
            className="time-btn"
            style={{
              padding: '6px 12px',
              fontSize: '0.85rem',
              fontWeight: activeTab === 'transactions' ? 600 : 400,
              color: activeTab === 'transactions' ? 'var(--text-primary)' : 'var(--text-muted)',
              borderBottom: activeTab === 'transactions' ? '2px solid var(--text-primary)' : 'none',
              borderRadius: 0,
            }}
            onClick={() => setActiveTab('transactions')}
          >
            Recent Transactions ({platform.transactions?.length || 0})
          </button>
        </div>

        {/* Holdings List */}
        {activeTab === 'holdings' ? (
          <div>
            <table className="holdings-table">
              <thead>
                <tr>
                  <th>Holding</th>
                  <th className="num-cell">Current Value</th>
                  <th className="num-cell">Today</th>
                </tr>
              </thead>
              <tbody>
                {platform.holdings && platform.holdings.length > 0 ? (
                  platform.holdings.map((h) => {
                    const isGain = (h.dayChange || 0) >= 0;
                    return (
                      <tr key={h.id}>
                        <td>
                          <div className="holding-name">{h.name}</div>
                          <div className="holding-meta">
                            {h.units ? `${h.units} units • ` : ''}
                            {h.type}
                          </div>
                        </td>
                        <td className="num-cell">
                          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                            {formatINR(h.currentValue)}
                          </div>
                          {h.invested && (
                            <div className="holding-meta">
                              Inv: {formatINR(h.invested)}
                            </div>
                          )}
                        </td>
                        <td className={`num-cell ${isGain ? 'positive' : 'negative'}`} style={{ color: isGain ? 'var(--positive)' : 'var(--negative)' }}>
                          <div>{formatINR(h.dayChange, { showSign: true })}</div>
                          {h.dayChangePercent !== undefined && (
                            <div style={{ fontSize: '0.74rem' }}>
                              {formatPercent(h.dayChangePercent, true)}
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan="3" style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                      No individual holdings recorded.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        ) : (
          /* Transactions List */
          <div className="activity-list" style={{ marginBottom: 32 }}>
            {platform.transactions && platform.transactions.length > 0 ? (
              platform.transactions.map((tx) => (
                <div key={tx.id} className="activity-item">
                  <div>
                    <div className="activity-name">{tx.type} — {tx.asset}</div>
                    <div className="activity-date">{tx.date}</div>
                  </div>
                  <div className="activity-right">
                    <div className="activity-amount">{formatINR(tx.amount)}</div>
                    <div className="activity-status">{tx.status}</div>
                  </div>
                </div>
              ))
            ) : (
              <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                No recent transactions found.
              </div>
            )}
          </div>
        )}

        {/* Drawer Footer Actions */}
        <div style={{ marginTop: 'auto', paddingTop: 20, borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button
            className="icon-btn"
            style={{ color: 'var(--negative)', borderColor: 'transparent' }}
            onClick={() => {
              if (window.confirm(`Disconnect ${platform.name}? This will remove its holdings from your Total Wealth.`)) {
                onDisconnect(platform.id);
                onClose();
              }
            }}
          >
            <Trash2 size={14} />
            <span>Disconnect Platform</span>
          </button>

          <button className="btn-secondary" onClick={onClose}>
            Done
          </button>
        </div>
      </aside>
    </div>
  );
}
