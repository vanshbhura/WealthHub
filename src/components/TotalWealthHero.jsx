import React from 'react';
import { formatINR, formatPercent } from '../utils/formatters';
import { TotalWealthHeroSkeleton } from './Skeletons';

export default function TotalWealthHero({
  summary,
  currentTotal,
  dayChange,
  dayChangePercent,
  investedAmount,
  totalProfitLoss,
  totalReturnPercentage,
  isLoading = false,
  isError = false,
  errorMessage = null,
  onRetry = null,
  onConnectFirst = null,
}) {
  if (isLoading) {
    return <TotalWealthHeroSkeleton />;
  }

  if (isError) {
    return (
      <section className="wealth-hero" aria-label="Total Wealth Overview">
        <div className="wealth-label">TOTAL WEALTH</div>
        <div style={{ padding: '16px 0', color: 'var(--text-danger, #ef4444)' }}>
          <p style={{ margin: '0 0 10px 0', fontSize: '0.95rem', fontWeight: 500 }}>
            {errorMessage || 'Unable to load total wealth.'}
          </p>
          {onRetry && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onRetry}
              style={{ fontSize: '0.82rem', padding: '5px 14px' }}
            >
              Retry
            </button>
          )}
        </div>
      </section>
    );
  }

  const totalWealth = summary?.total_wealth ?? currentTotal ?? 0;
  const investedValue = summary?.invested_value ?? summary?.invested_amount ?? investedAmount ?? 0;
  const profitLoss = summary?.profit_loss ?? summary?.total_profit_loss ?? totalProfitLoss ?? (totalWealth - investedValue);
  const profitLossPct = summary?.profit_loss_percentage ?? summary?.total_return_percentage ?? totalReturnPercentage ?? (investedValue > 0 ? (profitLoss / investedValue) * 100 : undefined);
  const dayChangeVal = summary?.today_change !== undefined ? summary?.today_change : dayChange;
  const dayChangePctVal = summary?.today_change_percentage !== undefined ? summary?.today_change_percentage : dayChangePercent;
  const assetCount = summary?.asset_count ?? 0;

  const isEmpty = totalWealth === 0 && investedValue === 0 && assetCount === 0;

  // Movement indicator
  const hasDayChange = dayChangeVal !== null && dayChangeVal !== undefined;
  const isPositiveDay = hasDayChange && dayChangeVal > 0;
  const isNegativeDay = hasDayChange && dayChangeVal < 0;

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
          {onConnectFirst && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onConnectFirst}
              style={{ marginLeft: 10, fontSize: '0.8rem', padding: '2px 10px' }}
            >
              + Connect
            </button>
          )}
        </div>
      ) : hasDayChange ? (
        <div className={`change-indicator ${isPositiveDay ? 'positive' : isNegativeDay ? 'negative' : 'neutral'}`}>
          <span>{formatINR(dayChangeVal, { showSign: true })} today</span>
          {dayChangePctVal !== null && dayChangePctVal !== undefined && (
            <span>({formatPercent(dayChangePctVal, true)})</span>
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
