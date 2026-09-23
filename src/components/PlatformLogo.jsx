import React, { useState } from 'react';

// Curated brand accents for known financial platforms
const PLATFORM_COLORS = {
  groww: '#00d09c',
  zerodha: '#387ed1',
  sbi: '#280071',
  'hdfc-bank': '#004c8f',
  'icici-bank': '#f58220',
  'axis-bank': '#97144d',
  'kotak-bank': '#ed1c24',
  lendenclub: '#2b59ff',
  jar: '#ffc107',
  phonepe: '#5f259f',
  coindcx: '#1c62f2',
  'cams-kfintech-cas': '#00838f',
  epfo: '#2e7d32',
  nps: '#e65100',
  upstox: '#5d3ebc',
  'angel-one': '#e23744',
  dhan: '#3272f7',
  'account-aggregator': '#0284c7',
};

export default function PlatformLogo({
  platform,
  size = 36,
  fontSize = '0.95rem',
  className = '',
  style = {}
}) {
  const [imageError, setImageError] = useState(false);

  const name = platform?.platform_name || platform?.name || 'Platform';
  const slug = platform?.platform_slug || platform?.slug || name.toLowerCase().replace(/[^a-z0-9]/g, '-');
  const logoUrl = platform?.logo_url;
  const accentColor = PLATFORM_COLORS[slug] || platform?.accentColor || '#475569';

  const initial = (name.charAt(0) || 'P').toUpperCase();

  // If logo_url exists and hasn't errored out, attempt to render it with fallback to initials
  if (logoUrl && !imageError) {
    return (
      <div
        className={`platform-logo-wrapper ${className}`}
        style={{
          width: size,
          height: size,
          minWidth: size,
          borderRadius: 'var(--radius-sm, 6px)',
          background: 'var(--bg-subtle, #f1f5f9)',
          border: '1px solid var(--border-subtle, #e2e8f0)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
          ...style
        }}
      >
        <img
          src={logoUrl}
          alt={`${name} logo`}
          onError={() => setImageError(true)}
          style={{
            width: '80%',
            height: '80%',
            objectFit: 'contain'
          }}
        />
      </div>
    );
  }

  // Graceful clean fallback: initials with brand accent
  return (
    <div
      className={`platform-badge-logo ${className}`}
      style={{
        width: size,
        height: size,
        minWidth: size,
        borderRadius: 'var(--radius-sm, 6px)',
        backgroundColor: accentColor,
        color: '#ffffff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 600,
        fontSize,
        boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
        ...style
      }}
      aria-label={`${name} logo`}
    >
      {initial}
    </div>
  );
}
