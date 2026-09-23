import React from 'react';
import { formatINR } from '../utils/formatters';

export default function RecentActivity({ platforms }) {
  // Aggregate recent transactions across all connected platforms
  const allActivities = [];

  platforms.forEach((platform) => {
    if (platform.transactions) {
      platform.transactions.forEach((tx) => {
        allActivities.push({
          ...tx,
          platformName: platform.name,
          accentColor: platform.accentColor,
        });
      });
    }
  });

  // Sort descending by date
  allActivities.sort((a, b) => new Date(b.date) - new Date(a.date));
  const recentItems = allActivities.slice(0, 5);

  if (recentItems.length === 0) return null;

  return (
    <section className="activity-section" aria-label="Recent Account Activity">
      <div className="activity-header">
        <h3 className="activity-title">RECENT ACTIVITY & CASHFLOWS</h3>
        <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
          Normalized across platforms
        </span>
      </div>

      <div className="activity-list">
        {recentItems.map((item) => (
          <div key={`${item.platformName}-${item.id}`} className="activity-item">
            <div className="activity-left">
              <span
                className="activity-platform-tag"
                style={{ borderColor: item.accentColor || 'var(--border-subtle)' }}
              >
                {item.platformName}
              </span>
              <div>
                <div className="activity-name">{item.type} — {item.asset}</div>
                <div className="activity-date">{item.date}</div>
              </div>
            </div>

            <div className="activity-right">
              <div className="activity-amount">{formatINR(item.amount)}</div>
              <div className="activity-status">{item.status}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
