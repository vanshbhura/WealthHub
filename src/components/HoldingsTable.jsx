import React from 'react';
import { formatINR, formatPercent } from '../utils/formatters';

export default function HoldingsTable({ holdings = [], isLoading = false }) {
  if (isLoading) {
    return (
      <div style={{ padding: '32px 0', textAlign: 'center', opacity: 0.6 }}>
        <span>Loading holdings...</span>
      </div>
    );
  }

  if (!holdings || holdings.length === 0) {
    return (
      <div
        style={{
          padding: '40px 24px',
          textAlign: 'center',
          background: 'var(--bg-surface, #ffffff)',
          border: '1px dashed var(--border-subtle, #e2e8f0)',
          borderRadius: 'var(--radius-md, 10px)',
          color: 'var(--text-muted, #94a3b8)',
        }}
      >
        <p style={{ fontWeight: 500, color: 'var(--text-primary, #0f172a)', marginBottom: 4 }}>
          No individual holdings recorded.
        </p>
        <p style={{ fontSize: '0.85rem' }}>
          This platform's balance is tracked at the account level.
        </p>
      </div>
    );
  }

  return (
    <div className="table-responsive" style={{ overflowX: 'auto', width: '100%' }}>
      <table className="wealth-table">
        <thead>
          <tr>
            <th scope="col">Asset</th>
            <th scope="col">Type</th>
            <th scope="col" style={{ textAlign: 'right' }}>Quantity</th>
            <th scope="col" style={{ textAlign: 'right' }}>Invested</th>
            <th scope="col" style={{ textAlign: 'right' }}>Current Value</th>
            <th scope="col" style={{ textAlign: 'right' }}>P&L</th>
            <th scope="col" style={{ textAlign: 'right' }}>Return %</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((item) => {
            const pnl = item.profit_loss !== undefined ? item.profit_loss : (item.current_value - item.invested_value);
            const pnlPct = item.profit_loss_percentage;
            const isPositive = pnl >= 0;

            const name = item.name || item.symbol || 'Holding';
            const symbol = item.symbol && item.symbol !== name ? item.symbol : null;
            const assetType = (item.asset_type || 'OTHER').replace(/_/g, ' ');

            return (
              <tr key={item.id || name}>
                <td style={{ fontWeight: 500 }}>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ color: 'var(--text-primary)' }}>{name}</span>
                    {symbol && (
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{symbol}</span>
                    )}
                  </div>
                </td>
                <td style={{ textTransform: 'capitalize', color: 'var(--text-secondary)' }}>
                  {assetType.toLowerCase()}
                </td>
                <td style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                  {item.quantity !== undefined && item.quantity !== null
                    ? Number(item.quantity).toLocaleString('en-IN', { maximumFractionDigits: 4 })
                    : '—'}
                </td>
                <td style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                  {formatINR(item.invested_value)}
                </td>
                <td style={{ textAlign: 'right', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
                  {formatINR(item.current_value)}
                </td>
                <td
                  style={{
                    textAlign: 'right',
                    fontVariantNumeric: 'tabular-nums',
                    color: pnl === null ? 'var(--text-muted)' : (isPositive ? 'var(--positive)' : 'var(--negative)')
                  }}
                >
                  {formatINR(pnl, { showSign: true })}
                </td>
                <td
                  style={{
                    textAlign: 'right',
                    fontWeight: 500,
                    fontVariantNumeric: 'tabular-nums',
                    color: pnlPct === null ? 'var(--text-muted)' : (isPositive ? 'var(--positive)' : 'var(--negative)')
                  }}
                >
                  {formatPercent(pnlPct, true)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
