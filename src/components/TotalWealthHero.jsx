import React from 'react';
import { formatINR, formatPercent } from '../utils/formatters';
import { TotalWealthHeroSkeleton } from './Skeletons';

export default function TotalWealthHero({
  summary,
  isLoading = false
}) {
  if (isLoading) {
    return <TotalWealthHeroSkeleton />;
  }

  const totalWealth = summary?.total_wealth ?? 0;
  const investedValue = summary?.invested_value ?? 0;
  const profitLoss = summary?.profit_loss ?? 0;
  const profitLossPct = summary?.profit_loss_percentage;
  const dayChange = summary?.today_change;
  const dayChangePct = summary?.today_change_percentage;
  const assetCount = summary?.asset_count ?? 0;

  const isEmpty = totalWealth === 0 && investedValue === 0 && assetCount === 0;

  // Movement indicator
  const hasDayChange = dayChange !== null && dayChange !== undefined;
  const isPositiveDay = hasDayChange && dayChange > 0;
  const isNegativeDay = hasDayChange && dayChange < 0;
  const isZeroDay = hasDayChange && dayChange === 0;

  // P&L indicator
  const hasPnl = profitLoss !== null && profitLoss !== undefined;
  const isPositivePnl = hasPnl && profitLoss > 0;
  const isNegativePnl = hasPnl && profitLoss < 0;

  return (
    <section className="wealth-hero" aria-label="Total Wealth Overview">
      <div className="wealth-label">TOTAL WEALTH</div>
      <div className="wealth-number">{formatINR(totalWealth)}</div>

      {isEmpty ? (
        <div className="change-indicator neutral" style={{ marginTop: 8, fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          <span>No investments connected yet.</span>
        </div>
      ) : hasDayChange ? (
        <div className={`change-indicator ${isPositiveDay ? 'positive' : isNegativeDay ? 'negative' : 'neutral'}`}>
          <span>{formatINR(dayChange, { showSign: true })} today</span>
          {dayChangePct !== null && dayChangePct !== undefined && (
            <span>({formatPercent(dayChangePct, true)})</span>
          )}
        </div>
      ) : (
        <div className="change-indicator neutral">
          <span>Not enough history yet.</span>
        </div>
      )}

      {/* Secondary Metrics Row: Invested, Current Value, P&L, Return % */}
      {!isEmpty && (
        <div className="wealth-metrics-row">
          <div className="metric-box">
            <span className="metric-label">Invested</span>
            <span className="metric-val">{formatINR(investedValue)}</span>
          </div>

          <div className="metric-box">
            <span className="metric-label">Current Value</span>
            <span className="metric-val">{formatINR(totalWealth)}</span>
          </div>

          <div className="metric-box">
            <span className="metric-label">P&L</span>
            <span
              className="metric-val"
              style={{
                color: isPositivePnl
                  ? 'var(--positive, #059669)'
                  : isNegativePnl
                  ? 'var(--negative, #dc2626)'
                  : 'var(--text-primary)'
              }}
            >
              {formatINR(profitLoss, { showSign: true })}
            </span>
          </div>

          <div className="metric-box">
            <span className="metric-label">Return %</span>
            <span
              className="metric-val"
              style={{
                color: isPositivePnl
                  ? 'var(--positive, #059669)'
                  : isNegativePnl
                  ? 'var(--negative, #dc2626)'
                  : 'var(--text-primary)'
              }}
            >
              {formatPercent(profitLossPct, true)}
            </span>
          </div>
        </div>
      )}
    </section>
  );
}
