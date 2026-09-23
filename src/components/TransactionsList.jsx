import React from 'react';
import { formatINR } from '../utils/formatters';

export default function TransactionsList({ transactions = [], isLoading = false }) {
  if (isLoading) {
    return (
      <div style={{ padding: '32px 0', textAlign: 'center', opacity: 0.6 }}>
        <span>Loading transactions...</span>
      </div>
    );
  }

  if (!transactions || transactions.length === 0) {
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
          No transactions recorded.
        </p>
        <p style={{ fontSize: '0.85rem' }}>
          Historical buy, sell, deposit, and dividend events will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="table-responsive" style={{ overflowX: 'auto', width: '100%' }}>
      <table className="wealth-table">
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Asset / Description</th>
            <th scope="col">Type</th>
            <th scope="col" style={{ textAlign: 'right' }}>Amount</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((tx) => {
            const dateStr = tx.transaction_date
              ? new Date(tx.transaction_date).toLocaleDateString('en-IN', {
                  day: 'numeric',
                  month: 'short',
                  year: 'numeric'
                })
              : '—';

            const txType = (tx.transaction_type || 'OTHER').replace(/_/g, ' ');
            const isOutflow = ['BUY', 'WITHDRAWAL', 'TRANSFER_OUT', 'FEE', 'TAX'].includes(tx.transaction_type);

            return (
              <tr key={tx.id || `${tx.amount}-${dateStr}`}>
                <td style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                  {dateStr}
                </td>
                <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
                  {tx.asset_name || tx.metadata_json?.asset_name || 'Portfolio Transaction'}
                </td>
                <td>
                  <span
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: 4,
                      background: 'var(--bg-subtle, #f1f5f9)',
                      color: 'var(--text-secondary, #475569)',
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em'
                    }}
                  >
                    {txType}
                  </span>
                </td>
                <td
                  style={{
                    textAlign: 'right',
                    fontWeight: 600,
                    fontVariantNumeric: 'tabular-nums',
                    color: isOutflow ? 'var(--text-primary)' : 'var(--positive)'
                  }}
                >
                  {formatINR(tx.amount)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
