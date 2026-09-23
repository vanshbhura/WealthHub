import React from 'react';

export function TotalWealthHeroSkeleton() {
  return (
    <section className="wealth-hero" aria-busy="true" aria-label="Loading Total Wealth">
      <div className="skeleton-bar" style={{ width: 110, height: 14, marginBottom: 16 }} />
      <div className="skeleton-bar" style={{ width: 280, height: 48, marginBottom: 20 }} />
      <div className="skeleton-bar" style={{ width: 180, height: 26, marginBottom: 32 }} />

      <div className="wealth-metrics-row">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="metric-box">
            <div className="skeleton-bar" style={{ width: 60, height: 12, marginBottom: 8 }} />
            <div className="skeleton-bar" style={{ width: 90, height: 20 }} />
          </div>
        ))}
      </div>
    </section>
  );
}

export function WealthGraphSkeleton() {
  return (
    <section className="graph-card" aria-busy="true" aria-label="Loading Wealth Graph">
      <div className="graph-header" style={{ marginBottom: 24 }}>
        <div className="skeleton-bar" style={{ width: 220, height: 16 }} />
        <div className="skeleton-bar" style={{ width: 260, height: 28, borderRadius: 6 }} />
      </div>
      <div
        className="skeleton-bar"
        style={{
          width: '100%',
          height: 220,
          borderRadius: 8,
          opacity: 0.5
        }}
      />
    </section>
  );
}

export function PlatformCardSkeleton() {
  return (
    <article className="platform-card skeleton-card" aria-busy="true">
      <div className="card-top">
        <div className="platform-meta">
          <div className="skeleton-bar" style={{ width: 36, height: 36, borderRadius: 6 }} />
          <div className="skeleton-bar" style={{ width: 90, height: 16 }} />
        </div>
        <div className="skeleton-bar" style={{ width: 10, height: 10, borderRadius: '50%' }} />
      </div>
      <div className="card-value-block">
        <div className="skeleton-bar" style={{ width: 140, height: 28, marginBottom: 8 }} />
        <div className="skeleton-bar" style={{ width: 100, height: 16 }} />
      </div>
      <div className="card-bottom">
        <div className="skeleton-bar" style={{ width: 70, height: 12 }} />
        <div className="skeleton-bar" style={{ width: 90, height: 12 }} />
      </div>
    </article>
  );
}

export function InvestmentGridSkeleton() {
  return (
    <div className="investments-grid" aria-busy="true">
      <PlatformCardSkeleton />
      <PlatformCardSkeleton />
      <PlatformCardSkeleton />
    </div>
  );
}

export function TableSkeleton({ rows = 4, cols = 5 }) {
  return (
    <div className="table-responsive" aria-busy="true" style={{ width: '100%' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div className="skeleton-bar" style={{ width: '100%', height: 36, borderRadius: 6 }} />
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="skeleton-bar" style={{ width: '100%', height: 44, borderRadius: 4 }} />
        ))}
      </div>
    </div>
  );
}

// Aliases for convenience
export const GraphSkeleton = WealthGraphSkeleton;
export const CardSkeleton = InvestmentGridSkeleton;
export const HeroSkeleton = TotalWealthHeroSkeleton;

