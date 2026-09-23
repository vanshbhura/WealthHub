import React from 'react';

export default function Greeting({ userName = null }) {
  // Determine time-aware greeting
  const getGreetingTime = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  };

  const title = userName ? `${getGreetingTime()}, ${userName}.` : "Welcome back.";

  return (
    <div className="greeting-section" style={{ marginBottom: '28px' }}>
      <h2
        className="greeting-text"
        style={{
          fontSize: '1.2rem',
          fontWeight: 600,
          color: 'var(--text-primary, #0f172a)',
          letterSpacing: '-0.01em',
          marginBottom: '2px'
        }}
      >
        {title}
      </h2>
      <p style={{ fontSize: '0.88rem', color: 'var(--text-muted, #64748b)' }}>
        Here's your wealth at a glance.
      </p>
    </div>
  );
}
