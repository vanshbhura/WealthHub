import React from 'react';
import PlatformLogo from './PlatformLogo';
import { formatINR, formatPercent } from '../utils/formatters';

export default function PlatformCard({ platform, onClick }) {
  const name = platform.platform_name || platform.name || 'Platform';
  const currentValue = platform.current_value !== undefined ? platform.current_value : (platform.currentValue || 0);
  
  // Movement / P&L display
  const hasDayChange = platform.today_change !== undefined && platform.today_change !== null;
  const changeValue = hasDayChange ? platform.today_change : (platform.dayChange !== undefined ? platform.dayChange : platform.profit_loss);
  const changePct = hasDayChange ? platform.today_change_percentage : (platform.dayChangePercent !== undefined ? platform.dayChangePercent : platform.profit_loss_percentage);
  
  const hasMovement = changeValue !== null && changeValue !== undefined;
  const isPositive = hasMovement && changeValue >= 0;

  const category = platform.category || platform.tagline || 'Investment';
  
  // Format freshness
  let lastUpdated = 'Manual';
  const rawDate = platform.last_updated || platform.lastUpdated || platform.syncTimestamp;
  if (rawDate) {
    if (typeof rawDate === 'string' && (rawDate.includes('T') || rawDate.includes('-'))) {
      const d = new Date(rawDate);
      if (!isNaN(d.getTime())) {
        const now = new Date();
        const diffMinutes = Math.floor((now.getTime() - d.getTime()) / (1000 * 60));
        if (diffMinutes < 5) {
          lastUpdated = 'Synced just now';
        } else if (diffMinutes < 60) {
          lastUpdated = `${diffMinutes}m ago`;
        } else if (diffMinutes < 1440) {
          lastUpdated = `${Math.floor(diffMinutes / 60)}h ago`;
        } else {
          lastUpdated = d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
        }
      }
    } else {
      lastUpdated = rawDate;
    }
  }

  // Asset count
  const assetCount = platform.asset_count !== undefined 
    ? platform.asset_count 
    : (platform.assetCount !== undefined 
        ? platform.assetCount 
        : (Array.isArray(platform.holdings) ? platform.holdings.length : null));

  const status = (platform.status || 'CONNECTED').toLowerCase();

  return (
    <article
      className="platform-card"
      onClick={() => onClick && onClick(platform)}
      tabIndex={0}
      role="button"
      aria-label={`${name} portfolio details: ${formatINR(currentValue)}`}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          if (onClick) onClick(platform);
        }
      }}
    >
      <div className="card-top">
        <div className="platform-meta">
          <PlatformLogo platform={platform} size={34} />
          <div>
            <h3 className="platform-name">{name}</h3>
            <span className="card-asset-type">{category}</span>
          </div>
        </div>
        <div className="platform-status-indicator" title={`Status: ${status}`}>
          <span className={`status-dot ${status === 'connected' || status === 'synced' ? 'synced' : status === 'awaiting' ? 'awaiting' : ''}`} />
          <span className="status-label">
            {platform.slug === 'account-aggregator' || platform.category === 'AGGREGATOR'
              ? 'Sandbox'
              : status === 'synced' || status === 'connected'
              ? 'Connected'
              : status === 'awaiting'
              ? 'Awaiting'
              : 'Manual'}
          </span>
        </div>
      </div>

      <div className="card-value-block">
        <div className="card-current-value">{formatINR(currentValue)}</div>
        {hasMovement ? (
          <div className={`card-change-line ${isPositive ? 'positive' : 'negative'}`}>
            <span>{formatINR(changeValue, { showSign: true })}</span>
            {changePct !== null && changePct !== undefined && (
              <span>({formatPercent(changePct, true)})</span>
            )}
            <span className="change-label">{hasDayChange ? 'today' : 'returns'}</span>
          </div>
        ) : (
          <div className="card-change-line neutral">
            <span>No daily movement</span>
          </div>
        )}
      </div>

      <div className="card-bottom">
        <span className="card-asset-count">
          {assetCount !== null ? `${assetCount} asset${assetCount !== 1 ? 's' : ''}` : 'Portfolio'}
        </span>
        <span className="card-updated-time">{lastUpdated}</span>
      </div>
    </article>
  );
}
