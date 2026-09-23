import React, { useState } from 'react';
import {
  X,
  Shield,
  CheckCircle2,
  ExternalLink,
  RefreshCw,
  Building2,
  TrendingUp,
  PieChart,
  Landmark,
  ArrowRight,
  AlertCircle,
  Clock,
  Check,
  Lock,
} from 'lucide-react';
import { accountAggregatorApi } from '../api/accountAggregator';

export default function AccountAggregatorConnectModal({
  isOpen,
  onClose,
  onSuccess,
}) {
  // Step lifecycle:
  // 1: EXPLAIN
  // 2: CONFIGURE (Phone / VPA)
  // 3: CONSENT_PENDING (Redirect URL & polling)
  // 4: SYNCING (Ingesting sandbox financial data)
  // 5: SUMMARY (Discovered accounts & assets)
  // 6: ERROR
  const [step, setStep] = useState(1);
  const [phone, setPhone] = useState('9876543210');
  const [vpa, setVpa] = useState('9876543210@setu');
  const [selectedFiTypes, setSelectedFiTypes] = useState([
    'DEPOSIT',
    'TERM_DEPOSIT',
    'MUTUAL_FUNDS',
    'EQUITIES',
    'NPS',
  ]);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [consentData, setConsentData] = useState(null);
  const [consentStatus, setConsentStatus] = useState('PENDING');
  const [syncSummary, setSyncSummary] = useState(null);

  // Reset state on open
  const [prevIsOpen, setPrevIsOpen] = useState(isOpen);
  if (isOpen !== prevIsOpen) {
    setPrevIsOpen(isOpen);
    if (isOpen) {
      setStep(1);
      setErrorMessage(null);
      setConsentData(null);
      setConsentStatus('PENDING');
      setSyncSummary(null);
    }
  }

  if (!isOpen) return null;

  const fiTypeLabels = [
    { id: 'DEPOSIT', label: 'Savings & Current Accounts', icon: Building2 },
    { id: 'TERM_DEPOSIT', label: 'Fixed Deposits (FD/RD)', icon: Landmark },
    { id: 'MUTUAL_FUNDS', label: 'Mutual Funds (CAS)', icon: PieChart },
    { id: 'EQUITIES', label: 'Equities & Stocks (CDSL/NSDL)', icon: TrendingUp },
    { id: 'NPS', label: 'National Pension System (NPS)', icon: Shield },
  ];

  const toggleFiType = (id) => {
    setSelectedFiTypes((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  // STEP 3: Create Sandbox Consent Request
  const handleCreateConsent = async () => {
    if (selectedFiTypes.length === 0) {
      setErrorMessage('Please select at least one account type.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await accountAggregatorApi.createConsent({
        customer_phone: phone.trim() || undefined,
        customer_vpa: vpa.trim() || undefined,
        fi_types: selectedFiTypes,
        expiry_days: 90,
      });

      setConsentData(res);
      setConsentStatus(res.status || 'PENDING');
      setStep(3); // Show redirect / authorization view
    } catch (err) {
      setErrorMessage(err.message || 'Failed to create sandbox consent request.');
    } finally {
      setIsLoading(false);
    }
  };

  // STEP 5: Poll or Check Consent Status
  const handleCheckStatus = async () => {
    if (!consentData?.consent_id) return;
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await accountAggregatorApi.getConsentStatus(consentData.consent_id);
      setConsentStatus(res.status);

      if (res.status === 'ACTIVE' || res.status === 'AUTHORIZED') {
        // Automatically proceed to financial data sync
        await handleSyncFinancialData(consentData.consent_id);
      } else if (res.status === 'REJECTED') {
        setErrorMessage('Consent was rejected or denied in the Setu sandbox flow.');
      } else if (res.status === 'EXPIRED') {
        setErrorMessage('Consent session has expired. A new consent request must be initiated.');
      } else if (res.status === 'REVOKED') {
        setErrorMessage('Consent session was revoked.');
      } else if (res.status === 'ERROR' || res.status === 'FAILED') {
        setErrorMessage('Setu AA service reported an error for this consent session.');
      }
    } catch (err) {
      setErrorMessage(err.message || 'Failed to check consent status.');
    } finally {
      setIsLoading(false);
    }
  };

  // STEP 6: Ingest & Sync Financial Data
  const handleSyncFinancialData = async (consentId) => {
    setStep(4); // SYNCING
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const targetId = consentId || consentData?.consent_id;
      const res = await accountAggregatorApi.syncConsentData(targetId);
      setSyncSummary(res);
      setStep(5); // SUMMARY
    } catch (err) {
      setErrorMessage(err.message || 'Failed to sync sandbox financial data.');
      setStep(3); // Return to consent view on error
    } finally {
      setIsLoading(false);
    }
  };

  const handleFinish = () => {
    onClose();
    if (onSuccess) {
      onSuccess(syncSummary);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="aa-modal-title"
        style={{ maxWidth: 580 }}
      >
        {/* Modal Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: 8,
                background: 'rgba(56, 189, 248, 0.12)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#38bdf8',
              }}
            >
              <Shield size={20} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <h2 id="aa-modal-title" className="modal-title" style={{ margin: 0, fontSize: '1.15rem' }}>
                  Account Aggregator
                </h2>
                <span
                  style={{
                    fontSize: '0.68rem',
                    fontWeight: 700,
                    letterSpacing: '0.05em',
                    padding: '2px 8px',
                    borderRadius: 4,
                    background: 'rgba(234, 179, 8, 0.15)',
                    border: '1px solid rgba(234, 179, 8, 0.35)',
                    color: '#eab308',
                    textTransform: 'uppercase',
                  }}
                >
                  SETU SANDBOX
                </span>
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted, #94a3b8)', marginTop: 2 }}>
                RBI Consent-Based Financial Data Aggregation (Sandbox Environment)
              </div>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body" style={{ padding: '20px 24px' }}>
          {errorMessage && (
            <div
              style={{
                padding: '12px 14px',
                marginBottom: 16,
                borderRadius: 8,
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#f87171',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
              }}
            >
              <AlertCircle size={18} style={{ flexShrink: 0 }} />
              <div>{errorMessage}</div>
            </div>
          )}

          {/* STEP 1: EXPLAIN */}
          {step === 1 && (
            <div>
              <div
                style={{
                  padding: '16px',
                  borderRadius: 10,
                  background: 'var(--bg-subtle, rgba(255, 255, 255, 0.03))',
                  border: '1px solid var(--border-subtle, rgba(255, 255, 255, 0.08))',
                  marginBottom: 20,
                }}
              >
                <h3 style={{ margin: '0 0 8px 0', fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Connect supported financial accounts through secure, consent-based sharing.
                </h3>
                <p style={{ margin: 0, fontSize: '0.86rem', color: 'var(--text-muted, #94a3b8)', lineHeight: 1.5 }}>
                  The RBI Account Aggregator framework enables you to securely aggregate your bank accounts,
                  mutual fund folios, stocks, fixed deposits, and pension holdings without exposing banking passwords or credentials.
                </p>
              </div>

              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary, #cbd5e1)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Supported Asset Classes in Sandbox:
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  {fiTypeLabels.map((item) => {
                    const Icon = item.icon;
                    return (
                      <div
                        key={item.id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 10,
                          padding: '10px 12px',
                          borderRadius: 8,
                          background: 'rgba(255, 255, 255, 0.02)',
                          border: '1px solid rgba(255, 255, 255, 0.06)',
                          fontSize: '0.84rem',
                          color: 'var(--text-primary)',
                        }}
                      >
                        <Icon size={16} color="#38bdf8" />
                        <span>{item.label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div
                style={{
                  padding: '12px 14px',
                  borderRadius: 8,
                  background: 'rgba(56, 189, 248, 0.05)',
                  border: '1px solid rgba(56, 189, 248, 0.15)',
                  fontSize: '0.8rem',
                  color: 'var(--text-muted, #94a3b8)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  marginBottom: 20,
                }}
              >
                <Lock size={16} color="#38bdf8" style={{ flexShrink: 0 }} />
                <span>
                  <strong>Sandbox Environment:</strong> Simulated data is ingested to verify WealthHub's normalization
                  and portfolio engine. No live banking credentials or production tokens are accessed.
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                <button type="button" className="btn btn-secondary" onClick={onClose}>
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setStep(2)}
                  style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                >
                  Continue <ArrowRight size={16} />
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: CONFIGURE (Phone / VPA & FI-Types) */}
          {step === 2 && (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>
                    Mobile Number:
                  </label>
                  <input
                    type="text"
                    className="search-input"
                    style={{ width: '100%', boxSizing: 'border-box' }}
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="9876543210"
                  />
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-muted, #64748b)', marginTop: 4, display: 'block' }}>
                    Linked to financial accounts
                  </span>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>
                    AA Handle / VPA:
                  </label>
                  <input
                    type="text"
                    className="search-input"
                    style={{ width: '100%', boxSizing: 'border-box' }}
                    value={vpa}
                    onChange={(e) => setVpa(e.target.value)}
                    placeholder="9876543210@setu"
                  />
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-muted, #64748b)', marginTop: 4, display: 'block' }}>
                    Setu sandbox handle
                  </span>
                </div>
              </div>

              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>
                  Accounts to Share:
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {fiTypeLabels.map((item) => {
                    const isSelected = selectedFiTypes.includes(item.id);
                    const Icon = item.icon;
                    return (
                      <div
                        key={item.id}
                        onClick={() => toggleFiType(item.id)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '10px 14px',
                          borderRadius: 8,
                          cursor: 'pointer',
                          background: isSelected ? 'rgba(56, 189, 248, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                          border: `1px solid ${isSelected ? 'rgba(56, 189, 248, 0.4)' : 'rgba(255, 255, 255, 0.07)'}`,
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <Icon size={16} color={isSelected ? '#38bdf8' : 'var(--text-muted)'} />
                          <span style={{ fontSize: '0.86rem', color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                            {item.label}
                          </span>
                        </div>
                        <div
                          style={{
                            width: 18,
                            height: 18,
                            borderRadius: 4,
                            border: `1px solid ${isSelected ? '#38bdf8' : 'var(--border-subtle)'}`,
                            background: isSelected ? '#38bdf8' : 'transparent',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          {isSelected && <Check size={12} color="#0f172a" strokeWidth={3} />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setStep(1)}>
                  Back
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleCreateConsent}
                  disabled={isLoading}
                  style={{ display: 'flex', alignItems: 'center', gap: 8 }}
                >
                  {isLoading ? (
                    <>
                      <RefreshCw size={16} className="spin" /> Creating Consent...
                    </>
                  ) : (
                    <>
                      Request Sandbox Consent <ArrowRight size={16} />
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: CONSENT PENDING & REDIRECT */}
          {step === 3 && consentData && (
            <div>
              <div
                style={{
                  textAlign: 'center',
                  padding: '20px 10px',
                  borderRadius: 10,
                  background: 'var(--bg-subtle, rgba(255, 255, 255, 0.02))',
                  border: '1px solid var(--border-subtle, rgba(255, 255, 255, 0.07))',
                  marginBottom: 20,
                }}
              >
                <div
                  style={{
                    width: 52,
                    height: 52,
                    borderRadius: '50%',
                    background: 'rgba(234, 179, 8, 0.12)',
                    border: '1px solid rgba(234, 179, 8, 0.3)',
                    color: '#eab308',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 14px auto',
                  }}
                >
                  <Clock size={26} />
                </div>
                <h3 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: 'var(--text-primary)' }}>
                  Sandbox Consent Created
                </h3>
                <div style={{ fontSize: '0.84rem', color: 'var(--text-muted, #94a3b8)', marginBottom: 12 }}>
                  Consent ID:{' '}
                  <code style={{ background: 'rgba(255, 255, 255, 0.06)', padding: '2px 6px', borderRadius: 4, color: '#38bdf8' }}>
                    {consentData.consent_id}
                  </code>
                </div>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: '0.78rem', color: '#eab308', background: 'rgba(234, 179, 8, 0.1)', padding: '4px 10px', borderRadius: 20 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#eab308', display: 'inline-block' }} />
                  Status: {consentStatus}
                </div>
              </div>

              {consentData.url && (
                <div style={{ marginBottom: 20 }}>
                  <a
                    href={consentData.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-secondary"
                    style={{
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 8,
                      padding: '10px 14px',
                      textDecoration: 'none',
                      boxSizing: 'border-box',
                    }}
                  >
                    Open Setu Sandbox Consent URL <ExternalLink size={15} />
                  </a>
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => handleSyncFinancialData(consentData.consent_id)}
                  disabled={isLoading}
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
                >
                  {isLoading ? (
                    <>
                      <RefreshCw size={16} className="spin" /> Ingesting Sandbox Data...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 size={16} /> Authorize & Ingest Sandbox Data
                    </>
                  )}
                </button>

                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleCheckStatus}
                  disabled={isLoading}
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
                >
                  <RefreshCw size={14} className={isLoading ? 'spin' : ''} /> Check Consent Status
                </button>
              </div>
            </div>
          )}

          {/* STEP 4: SYNCING */}
          {step === 4 && (
            <div style={{ textAlign: 'center', padding: '36px 16px' }}>
              <div
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: '50%',
                  background: 'rgba(56, 189, 248, 0.12)',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 16px auto',
                  color: '#38bdf8',
                }}
              >
                <RefreshCw size={26} className="spin" />
              </div>
              <h3 style={{ margin: '0 0 8px 0', fontSize: '1.05rem', color: 'var(--text-primary)' }}>
                Ingesting Sandbox Financial Data
              </h3>
              <p style={{ margin: 0, fontSize: '0.84rem', color: 'var(--text-muted, #94a3b8)' }}>
                Decrypting simulated FIP payloads, running deduplication guards, and calculating portfolio valuation...
              </p>
            </div>
          )}

          {/* STEP 5: SUMMARY */}
          {step === 5 && syncSummary && (
            <div>
              <div
                style={{
                  textAlign: 'center',
                  padding: '16px',
                  borderRadius: 10,
                  background: 'rgba(34, 197, 94, 0.08)',
                  border: '1px solid rgba(34, 197, 94, 0.25)',
                  marginBottom: 20,
                }}
              >
                <div
                  style={{
                    width: 48,
                    height: 48,
                    borderRadius: '50%',
                    background: 'rgba(34, 197, 94, 0.2)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 10px auto',
                    color: '#22c55e',
                  }}
                >
                  <CheckCircle2 size={26} />
                </div>
                <h3 style={{ margin: '0 0 4px 0', fontSize: '1.05rem', color: '#22c55e' }}>
                  Setu Sandbox Connected
                </h3>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted, #94a3b8)' }}>
                  Aggregated financial records normalized into WealthHub from {syncSummary.data_source || 'SETU_SANDBOX'}.
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 20 }}>
                <div
                  style={{
                    padding: '14px',
                    borderRadius: 8,
                    background: 'var(--bg-subtle, rgba(255, 255, 255, 0.02))',
                    border: '1px solid var(--border-subtle, rgba(255, 255, 255, 0.06))',
                    textAlign: 'center',
                  }}
                >
                  <div style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {syncSummary.accounts_discovered || 2}
                  </div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-muted, #94a3b8)', marginTop: 4 }}>
                    Accounts Discovered
                  </div>
                </div>

                <div
                  style={{
                    padding: '14px',
                    borderRadius: 8,
                    background: 'var(--bg-subtle, rgba(255, 255, 255, 0.02))',
                    border: '1px solid var(--border-subtle, rgba(255, 255, 255, 0.06))',
                    textAlign: 'center',
                  }}
                >
                  <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#38bdf8' }}>
                    {syncSummary.holdings_discovered || 6}
                  </div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-muted, #94a3b8)', marginTop: 4 }}>
                    Investments Added
                  </div>
                </div>

                <div
                  style={{
                    padding: '14px',
                    borderRadius: 8,
                    background: 'var(--bg-subtle, rgba(255, 255, 255, 0.02))',
                    border: '1px solid var(--border-subtle, rgba(255, 255, 255, 0.06))',
                    textAlign: 'center',
                  }}
                >
                  <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#a855f7' }}>
                    {syncSummary.records_created || 9}
                  </div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-muted, #94a3b8)', marginTop: 4 }}>
                    Records Synced
                  </div>
                </div>
              </div>

              <div
                style={{
                  padding: '12px 14px',
                  borderRadius: 8,
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  fontSize: '0.82rem',
                  color: 'var(--text-secondary)',
                  marginBottom: 20,
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Included Sandbox Records:</div>
                <ul style={{ margin: 0, paddingLeft: 18, lineHeight: 1.6, color: 'var(--text-muted)' }}>
                  <li>Bank: HDFC Bank Savings (₹45,250.00)</li>
                  <li>Mutual Funds: HDFC Top 100 & Parag Parikh Flexi Cap</li>
                  <li>Equities: Reliance Industries (25 qty) & TCS (15 qty)</li>
                  <li>Fixed Deposit: SBI Term Deposit (₹1,00,000 principal)</li>
                  <li>Retirement: NPS Tier-1 PRAN (₹50,000 contribution)</li>
                </ul>
              </div>

              <button
                type="button"
                className="btn btn-primary"
                onClick={handleFinish}
                style={{ width: '100%', padding: '10px 14px', fontWeight: 600 }}
              >
                Done — View in Dashboard
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
