import React from 'react';
import PlatformCard from './PlatformCard';
import AddPlatformCard from './AddPlatformCard';
import { CardSkeleton } from './Skeletons';

export default function InvestmentGrid({
  platforms = [],
  onSelectPlatform,
  onOpenAddPlatform,
  onRetry,
  isLoading = false,
  isError = false
}) {
  return (
    <section className="investments-section" aria-label="Your Connected Platforms">
      <div className="section-header">
        <div className="section-title-group">
          <h2 className="section-title">YOUR INVESTMENTS</h2>
          {!isLoading && !isError && (
            <span className="section-subtitle">
              {platforms.length} platform{platforms.length !== 1 ? 's' : ''} connected
            </span>
          )}
        </div>
      </div>

      {isLoading ? (
        <CardSkeleton count={4} />
      ) : isError ? (
        <div
          style={{
            padding: '36px 24px',
            textAlign: 'center',
            background: 'rgba(239, 68, 68, 0.05)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: '10px',
            marginBottom: '20px'
          }}
        >
          <p style={{ fontSize: '0.95rem', fontWeight: 500, color: 'var(--text-danger, #ef4444)', marginBottom: '8px' }}>
            Unable to load portfolio data.
          </p>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted, #94a3b8)', marginBottom: '16px' }}>
            There was an issue communicating with the WealthHub engine.
          </p>
          {onRetry && (
            <button
              className="btn-secondary"
              onClick={onRetry}
              style={{
                padding: '7px 16px',
                borderRadius: '6px',
                background: 'transparent',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                fontSize: '0.85rem'
              }}
            >
              Retry
            </button>
          )}
        </div>
      ) : platforms.length === 0 ? (
        <div
          style={{
            padding: '48px 24px',
            textAlign: 'center',
            background: 'var(--card-bg, #ffffff)',
            border: '1px dashed var(--border, #e2e8f0)',
            borderRadius: '10px',
            marginBottom: '20px'
          }}
        >
          <p style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '8px', color: 'var(--text-primary, #0f172a)' }}>
            No investments connected yet.
          </p>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted, #64748b)', marginBottom: '20px', maxWidth: 420, margin: '0 auto 20px auto', lineHeight: 1.5 }}>
            Connect your broker, bank account, mutual funds, or digital gold to calculate your real-time total wealth.
          </p>
          <button
            className="btn-primary"
            onClick={onOpenAddPlatform}
            style={{
              padding: '9px 18px',
              borderRadius: '6px',
              background: 'var(--accent, #0f172a)',
              color: '#ffffff',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 500,
              fontSize: '0.9rem'
            }}
          >
            + Connect Platform
          </button>
        </div>
      ) : (
        <div className="investments-grid">
          {platforms.map((platform) => (
            <PlatformCard
              key={platform.id || platform.platform_id}
              platform={platform}
              onClick={onSelectPlatform}
            />
          ))}

          {/* '+' Add Platform card always at the end */}
          <AddPlatformCard onClick={onOpenAddPlatform} />
        </div>
      )}
    </section>
  );
}
