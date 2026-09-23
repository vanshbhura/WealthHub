import React, { useState } from 'react';
import { X, Lock, Mail, User, ShieldCheck } from 'lucide-react';
import { authApi } from '../api/auth';

export default function AuthModal({ isOpen, onClose, onAuthSuccess }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      let data;
      if (isRegister) {
        data = await authApi.register(email, password, fullName);
      } else {
        data = await authApi.login(email, password);
      }
      onAuthSuccess(data.user);
      onClose();
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-card"
        style={{ maxWidth: 420 }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="modal-header">
          <h2 className="modal-title">{isRegister ? 'Create Account' : 'Sign In to WealthHub'}</h2>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          <form onSubmit={handleSubmit}>
            {error && (
              <div
                style={{
                  background: 'var(--negative-bg)',
                  color: 'var(--negative)',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.82rem',
                  marginBottom: 16,
                  border: '1px solid var(--negative)',
                }}
              >
                {error}
              </div>
            )}

            {isRegister && (
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  Full Name
                </label>
                <div style={{ position: 'relative' }}>
                  <User size={16} style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-muted)' }} />
                  <input
                    type="text"
                    required
                    placeholder="Aditya Sharma"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="search-input"
                    style={{ paddingLeft: 38 }}
                  />
                </div>
              </div>
            )}

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Email Address
              </label>
              <div style={{ position: 'relative' }}>
                <Mail size={16} style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-muted)' }} />
                <input
                  type="email"
                  required
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="search-input"
                  style={{ paddingLeft: 38 }}
                />
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Password (min 8 characters)
              </label>
              <div style={{ position: 'relative' }}>
                <Lock size={16} style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-muted)' }} />
                <input
                  type="password"
                  required
                  minLength={8}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="search-input"
                  style={{ paddingLeft: 38 }}
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn-primary"
              style={{ width: '100%', justifyContent: 'center', padding: '10px 16px', fontSize: '0.9rem' }}
              disabled={isLoading}
            >
              {isLoading ? 'Authenticating...' : isRegister ? 'Register' : 'Sign In'}
            </button>

            <div style={{ marginTop: 16, textAlign: 'center', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              {isRegister ? (
                <span>
                  Already have an account?{' '}
                  <button
                    type="button"
                    style={{ background: 'none', border: 'none', color: 'var(--text-primary)', fontWeight: 600, cursor: 'pointer', textDecoration: 'underline' }}
                    onClick={() => { setIsRegister(false); setError(null); }}
                  >
                    Sign In
                  </button>
                </span>
              ) : (
                <span>
                  New to WealthHub?{' '}
                  <button
                    type="button"
                    style={{ background: 'none', border: 'none', color: 'var(--text-primary)', fontWeight: 600, cursor: 'pointer', textDecoration: 'underline' }}
                    onClick={() => { setIsRegister(true); setError(null); }}
                  >
                    Create Account
                  </button>
                </span>
              )}
            </div>
          </form>

          <div className="security-note" style={{ marginTop: 20 }}>
            <ShieldCheck size={16} />
            <div>
              <strong>Production-Grade Isolation:</strong> All financial records, accounts, and transactions are strictly cryptographically segregated per user.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
