import React, { useState } from 'react';
import { X, Shield, Eye, EyeOff, Check, AlertCircle, RefreshCw, ArrowRight, ExternalLink } from 'lucide-react';
import PlatformLogo from './PlatformLogo';
import { connectionsApi } from '../api/connections';

export default function GrowwConnectModal({
  isOpen,
  onClose,
  platform,
  onSuccess
}) {
  const [accessToken, setAccessToken] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [ucc, setUcc] = useState('');

  // States: 'IDLE' | 'TESTING' | 'TEST_SUCCESS' | 'CONNECTING' | 'SYNCING' | 'SUCCESS' | 'ERROR'
  const [stage, setStage] = useState('IDLE');
  const [syncStepText, setSyncStepText] = useState('');
  const [errorMessage, setErrorMessage] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [syncSummary, setSyncSummary] = useState(null);

  if (!isOpen || !platform) return null;

  const handleTestConnection = async () => {
    if (!accessToken.trim()) {
      setErrorMessage('Please enter your Groww API access token.');
      return;
    }

    setErrorMessage(null);
    setStage('TESTING');

    try {
      const res = await connectionsApi.testConnection({
        platform_id: platform.id,
        connector_key: 'groww_direct',
        credentials: {
          access_token: accessToken.trim(),
          ucc: ucc.trim() || undefined,
        },
      });

      setTestResult(res);
      setStage('TEST_SUCCESS');
    } catch (err) {
      setStage('ERROR');
      const msg = err.response?.data?.error?.message || err.message || 'Authentication failed. Please check your token.';
      setErrorMessage(msg);
    }
  };

  const handleConnectAndSync = async () => {
    if (!accessToken.trim()) {
      setErrorMessage('Please enter your Groww API access token.');
      return;
    }

    setErrorMessage(null);
    setStage('CONNECTING');
    setSyncStepText('Authenticating and securing credentials...');

    try {
      // 1. Establish connection & store encrypted secrets
      const connRes = await connectionsApi.createConnection({
        platform_id: platform.id,
        connection_type: 'DIRECT_API',
        connector_key: 'groww_direct',
        external_account_reference: ucc.trim() || undefined,
        credentials: {
          access_token: accessToken.trim(),
          ucc: ucc.trim() || undefined,
        },
      });

      // 2. Trigger initial portfolio sync
      setStage('SYNCING');
      setSyncStepText('Fetching holdings, positions, and cash balances...');

      const syncRes = await connectionsApi.syncConnection(connRes.id);

      setSyncSummary({
        recordsProcessed: syncRes.records_processed,
        recordsCreated: syncRes.records_created,
        recordsUpdated: syncRes.records_updated,
      });

      setStage('SUCCESS');
      if (onSuccess) {
        onSuccess(connRes);
      }
    } catch (err) {
      setStage('ERROR');
      const msg = err.response?.data?.error?.message || err.message || 'Failed to establish live Groww connection.';
      setErrorMessage(msg);
    }
  };

  const handleClose = () => {
    if (stage === 'CONNECTING' || stage === 'SYNCING') return;
    setAccessToken('');
    setUcc('');
    setStage('IDLE');
    setErrorMessage(null);
    setTestResult(null);
    setSyncSummary(null);
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div
        className="modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="groww-connect-title"
        style={{ maxWidth: 540 }}
      >
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <PlatformLogo platform={platform} size={36} />
            <div>
              <h2 id="groww-connect-title" className="modal-title">
                Connect Groww Live API
              </h2>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Official Read-Only Portfolio Connection
              </div>
            </div>
          </div>
          <button
            className="modal-close-btn"
            onClick={handleClose}
            disabled={stage === 'CONNECTING' || stage === 'SYNCING'}
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Security Banner */}
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 10,
              padding: '12px 14px',
              borderRadius: 8,
              background: 'var(--bg-subtle, #f8fafc)',
              border: '1px solid var(--border-subtle, #e2e8f0)',
              fontSize: '0.82rem',
              color: 'var(--text-secondary, #475569)',
              lineHeight: 1.45,
            }}
          >
            <Shield size={18} color="var(--accent-muted, #0284c7)" style={{ flexShrink: 0, marginTop: 1 }} />
            <div>
              <strong>Secure & Read-Only:</strong> Your Groww API access token is encrypted at rest using AES-128 and used only to fetch your authorized portfolio data. We never ask for your Groww password and never place trades.
            </div>
          </div>

          {/* Subscription note */}
          <div
            style={{
              fontSize: '0.78rem',
              color: 'var(--text-muted, #64748b)',
              padding: '4px 2px',
            }}
          >
            Groww API access may require an active Groww Trading API subscription and provider-side authentication/approval.{' '}
            <a
              href="https://groww.in/trade-api"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: 'var(--accent-muted, #0284c7)', display: 'inline-flex', alignItems: 'center', gap: 2 }}
            >
              Learn more <ExternalLink size={11} />
            </a>
          </div>

          {/* Form Content / Multi-stage Display */}
          {stage === 'SUCCESS' ? (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                textAlign: 'center',
                padding: '24px 12px',
                gap: 12,
              }}
            >
              <div
                style={{
                  width: 52,
                  height: 52,
                  borderRadius: '50%',
                  background: 'var(--positive-bg, rgba(16, 185, 129, 0.1))',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--positive, #059669)',
                }}
              >
                <Check size={28} />
              </div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                Groww Connected & Synced!
              </h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', maxWidth: 400 }}>
                Your Groww Demat equity holdings and cash balances have been securely synchronized with your WealthHub portfolio.
              </p>
              {syncSummary && (
                <div
                  style={{
                    display: 'flex',
                    gap: 16,
                    marginTop: 8,
                    padding: '10px 18px',
                    borderRadius: 6,
                    background: 'var(--bg-subtle, #f1f5f9)',
                    fontSize: '0.82rem',
                  }}
                >
                  <div>
                    <strong>{syncSummary.recordsCreated}</strong> new records
                  </div>
                  <div>•</div>
                  <div>
                    <strong>{syncSummary.recordsUpdated}</strong> updated
                  </div>
                </div>
              )}
            </div>
          ) : stage === 'CONNECTING' || stage === 'SYNCING' ? (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                textAlign: 'center',
                padding: '36px 12px',
                gap: 16,
              }}
            >
              <RefreshCw
                size={36}
                color="var(--accent-muted, #0284c7)"
                style={{ animation: 'spin 1.2s linear infinite' }}
              />
              <div>
                <div style={{ fontSize: '0.98rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {stage === 'CONNECTING' ? 'Authenticating with Groww...' : 'Syncing Your Groww Portfolio...'}
                </div>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 4 }}>
                  {syncStepText}
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Token Input */}
              <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label
                  htmlFor="groww-access-token"
                  style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-primary)' }}
                >
                  API Access Token <span style={{ color: 'var(--danger, #ef4444)' }}>*</span>
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    id="groww-access-token"
                    type={showToken ? 'text' : 'password'}
                    className="form-input"
                    placeholder="Enter your Groww Trading API Bearer Token"
                    value={accessToken}
                    onChange={(e) => setAccessToken(e.target.value)}
                    disabled={stage === 'TESTING'}
                    style={{ paddingRight: 40, width: '100%' }}
                    autoComplete="off"
                  />
                  <button
                    type="button"
                    onClick={() => setShowToken(!showToken)}
                    style={{
                      position: 'absolute',
                      right: 10,
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: 4,
                    }}
                    title={showToken ? 'Hide token' : 'Show token'}
                  >
                    {showToken ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Generated from Groww Profile &gt; Settings &gt; Trading APIs.
                </span>
              </div>

              {/* Optional UCC / Client ID */}
              <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label
                  htmlFor="groww-ucc"
                  style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-primary)' }}
                >
                  Unique Client Code (UCC) <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>(Optional)</span>
                </label>
                <input
                  id="groww-ucc"
                  type="text"
                  className="form-input"
                  placeholder="e.g., 924189 (auto-detected from profile if omitted)"
                  value={ucc}
                  onChange={(e) => setUcc(e.target.value)}
                  disabled={stage === 'TESTING'}
                />
              </div>

              {/* Test Connection Result Banner */}
              {stage === 'TEST_SUCCESS' && testResult && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '10px 14px',
                    borderRadius: 6,
                    background: 'var(--positive-bg, rgba(16, 185, 129, 0.08))',
                    border: '1px solid rgba(16, 185, 129, 0.25)',
                    color: 'var(--positive, #059669)',
                    fontSize: '0.84rem',
                  }}
                >
                  <Check size={16} />
                  <span>
                    Credentials verified! UCC: <strong>{testResult.ucc || 'Detected'}</strong>. Ready to connect.
                  </span>
                </div>
              )}

              {/* Error Message */}
              {errorMessage && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 8,
                    padding: '10px 14px',
                    borderRadius: 6,
                    background: 'rgba(239, 68, 68, 0.08)',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                    color: 'var(--danger, #dc2626)',
                    fontSize: '0.84rem',
                  }}
                >
                  <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 2 }} />
                  <span>{errorMessage}</span>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 20 }}>
          {stage === 'SUCCESS' ? (
            <button
              type="button"
              className="btn-primary"
              onClick={handleClose}
              style={{
                padding: '8px 20px',
                borderRadius: 6,
                background: 'var(--accent, #0f172a)',
                color: '#ffffff',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              Done
            </button>
          ) : (
            <>
              <button
                type="button"
                className="btn-secondary"
                onClick={handleClose}
                disabled={stage === 'CONNECTING' || stage === 'SYNCING'}
                style={{
                  padding: '8px 16px',
                  borderRadius: 6,
                  border: '1px solid var(--border-subtle, #e2e8f0)',
                  background: 'transparent',
                  color: 'var(--text-primary)',
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>

              <button
                type="button"
                className="btn-secondary"
                onClick={handleTestConnection}
                disabled={stage === 'TESTING' || stage === 'CONNECTING' || stage === 'SYNCING' || !accessToken.trim()}
                style={{
                  padding: '8px 16px',
                  borderRadius: 6,
                  border: '1px solid var(--border-focus, #cbd5e1)',
                  background: 'var(--bg-subtle, #f1f5f9)',
                  color: 'var(--text-primary)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                {stage === 'TESTING' ? (
                  <>
                    <RefreshCw size={13} style={{ animation: 'spin 1s linear infinite' }} />
                    <span>Verifying...</span>
                  </>
                ) : (
                  <span>Test Connection</span>
                )}
              </button>

              <button
                type="button"
                className="btn-primary"
                onClick={handleConnectAndSync}
                disabled={stage === 'CONNECTING' || stage === 'SYNCING' || !accessToken.trim()}
                style={{
                  padding: '8px 20px',
                  borderRadius: 6,
                  background: 'var(--accent, #0f172a)',
                  color: '#ffffff',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <span>Connect & Sync</span>
                <ArrowRight size={14} />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
