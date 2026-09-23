import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Search, X, ArrowLeft, Shield, PlusCircle, Bell, Check, Info, UploadCloud } from 'lucide-react';
import { platformsApi } from '../api/platforms';
import PlatformLogo from './PlatformLogo';
import ManualAssetModal from './ManualAssetModal';
import StatementImportModal from './StatementImportModal';
import GrowwConnectModal from './GrowwConnectModal';
import AccountAggregatorConnectModal from './AccountAggregatorConnectModal';

const UI_CATEGORIES = [
  { label: 'All', value: 'ALL' },
  { label: 'Banks', value: 'BANK' },
  { label: 'Brokers', value: 'BROKER' },
  { label: 'Mutual Funds', value: 'MUTUAL_FUND' },
  { label: 'Gold', value: 'DIGITAL_GOLD' },
  { label: 'Silver', value: 'DIGITAL_SILVER' },
  { label: 'P2P', value: 'P2P' },
  { label: 'Crypto', value: 'CRYPTO' },
  { label: 'Retirement', value: 'RETIREMENT' },
  { label: 'Aggregators', value: 'AGGREGATOR' },
  { label: 'Other', value: 'OTHER' },
];

export default function AddPlatformModal({
  isOpen,
  onClose,
  connectedPlatformIds = [],
  onPlatformAdded
}) {
  const [catalog, setCatalog] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');

  // Step 2 state: Selected platform & its connectors
  const [selectedPlatform, setSelectedPlatform] = useState(null);
  const [connectors, setConnectors] = useState([]);
  const [isLoadingConnectors, setIsLoadingConnectors] = useState(false);
  const [notifiedConnectors, setNotifiedConnectors] = useState({});

  // Sub-Modals
  const [manualPlatform, setManualPlatform] = useState(null);
  const [importPlatform, setImportPlatform] = useState(null);
  const [growwPlatform, setGrowwPlatform] = useState(null);
  const [showAAModal, setShowAAModal] = useState(false);
  const [noticeMessage, setNoticeMessage] = useState(null);

  const isAAConnected = useMemo(() => {
    return (
      connectedPlatformIds.includes('account-aggregator') ||
      catalog.some(
        (p) => p.slug === 'account-aggregator' && connectedPlatformIds.includes(p.id)
      )
    );
  }, [connectedPlatformIds, catalog]);

  // Fetch catalog from backend GET /api/platforms
  const fetchCatalog = useCallback(() => {
    setIsLoading(true);
    setError(null);
    platformsApi.getPlatforms()
      .then(data => {
        setCatalog(data || []);
      })
      .catch(err => {
        console.error('Error fetching platforms catalog:', err);
        setError(err.message || 'Unable to load platforms catalog.');
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    fetchCatalog();
  }, [isOpen, fetchCatalog]);

  // When a platform is selected, fetch its supported connection methods
  useEffect(() => {
    if (!selectedPlatform) {
      setConnectors([]);
      return;
    }
    setIsLoadingConnectors(true);
    platformsApi.getPlatformConnectors(selectedPlatform.id || selectedPlatform.slug)
      .then(data => {
        setConnectors(data || []);
      })
      .catch(err => {
        console.error('Error fetching platform connectors:', err);
        // Fallback default connectors
        setConnectors([
          {
            connector_type: 'MANUAL',
            connector_key: 'manual_asset',
            name: 'Manual Entry',
            status: 'AVAILABLE',
            capabilities: ['HOLDINGS', 'TRANSACTIONS', 'BALANCES', 'ASSETS'],
            is_enabled: true,
            requirements: 'No credentials required'
          },
          {
            connector_type: 'IMPORT',
            connector_key: 'statement_import',
            name: 'Statement Import',
            status: 'COMING_SOON',
            capabilities: ['HOLDINGS', 'TRANSACTIONS', 'STATEMENTS'],
            is_enabled: false,
            requirements: 'CSV, Excel, or CAS statement'
          }
        ]);
      })
      .finally(() => {
        setIsLoadingConnectors(false);
      });
  }, [selectedPlatform]);

  // Filter catalog based on search query and category
  const filteredCatalog = useMemo(() => {
    return catalog.filter((p) => {
      const matchesCategory =
        selectedCategory === 'ALL' ||
        p.category === selectedCategory ||
        (selectedCategory === 'DIGITAL_GOLD' && p.category.includes('GOLD')) ||
        (selectedCategory === 'DIGITAL_SILVER' && p.category.includes('SILVER'));

      const matchesSearch =
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (p.description && p.description.toLowerCase().includes(searchQuery.toLowerCase()));

      return matchesCategory && matchesSearch;
    });
  }, [catalog, searchQuery, selectedCategory]);

  if (!isOpen) return null;

  const handleSelectPlatform = (platform) => {
    setSelectedPlatform(platform);
  };

  const handleBackToCatalog = () => {
    setSelectedPlatform(null);
    setConnectors([]);
  };

  const handleNotifyMe = (connectorKey) => {
    setNotifiedConnectors(prev => ({ ...prev, [connectorKey]: true }));
    setNoticeMessage(`We'll notify you as soon as this direct integration is live.`);
    setTimeout(() => setNoticeMessage(null), 4000);
  };

  const handleManualEntry = (platform) => {
    setManualPlatform(platform);
  };

  const handleClose = () => {
    setSelectedPlatform(null);
    setConnectors([]);
    setSearchQuery('');
    onClose();
  };

  return (
    <>
      <div className="modal-overlay" onClick={handleClose}>
        <div
          className="modal-card"
          onClick={(e) => e.stopPropagation()}
          role="dialog"
          aria-modal="true"
          aria-labelledby="add-platform-title"
          style={{ maxWidth: 660 }}
        >
          {/* Modal Header */}
          <div className="modal-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {selectedPlatform && (
                <button
                  type="button"
                  onClick={handleBackToCatalog}
                  className="icon-btn"
                  title="Back to all platforms"
                  style={{ border: 'none', padding: '4px 6px' }}
                >
                  <ArrowLeft size={16} />
                </button>
              )}
              <div>
                <h2 id="add-platform-title" className="modal-title">
                  {selectedPlatform ? `Connect ${selectedPlatform.name}` : 'Add a Platform'}
                </h2>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted, #64748b)', marginTop: 2 }}>
                  {selectedPlatform
                    ? 'Choose an available connection method below.'
                    : 'Select a platform to connect or add assets manually.'}
                </div>
              </div>
            </div>
            <button className="modal-close-btn" onClick={handleClose} aria-label="Close modal">
              <X size={18} />
            </button>
          </div>

          <div className="modal-body">
            {noticeMessage && (
              <div
                style={{
                  padding: '10px 14px',
                  marginBottom: 16,
                  borderRadius: 6,
                  background: 'var(--bg-subtle, #f1f5f9)',
                  border: '1px solid var(--border-subtle, #e2e8f0)',
                  color: 'var(--text-primary)',
                  fontSize: '0.85rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8
                }}
              >
                <Info size={16} color="var(--accent-muted, #0284c7)" />
                <span>{noticeMessage}</span>
              </div>
            )}

            {/* STEP 1: CATALOG VIEW */}
            {!selectedPlatform ? (
              <>
                {/* Search Input */}
                <div className="search-input-wrapper">
                  <Search className="search-icon" size={16} />
                  <input
                    type="text"
                    className="search-input"
                    placeholder="Search platforms (e.g., Groww, Zerodha, SBI, Jar)..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    autoFocus
                  />
                  {searchQuery && (
                    <button
                      className="modal-close-btn"
                      style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)' }}
                      onClick={() => setSearchQuery('')}
                    >
                      <X size={14} />
                    </button>
                  )}
                </div>

                {/* Category Chips */}
                <div className="category-chips" role="tablist">
                  {UI_CATEGORIES.map((cat) => (
                    <button
                      key={cat.value}
                      type="button"
                      className={`category-chip ${selectedCategory === cat.value ? 'active' : ''}`}
                      onClick={() => setSelectedCategory(cat.value)}
                    >
                      {cat.label}
                    </button>
                  ))}
                </div>

                {/* Primary Option: Connect via Account Aggregator */}
                <div
                  className="aa-primary-banner"
                  style={{
                    marginBottom: 16,
                    padding: '16px',
                    borderRadius: 10,
                    background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.08) 0%, rgba(30, 58, 138, 0.12) 100%)',
                    border: '1px solid rgba(56, 189, 248, 0.28)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 16,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div
                      style={{
                        width: 44,
                        height: 44,
                        borderRadius: 10,
                        background: 'rgba(56, 189, 248, 0.16)',
                        border: '1px solid rgba(56, 189, 248, 0.35)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#38bdf8',
                        flexShrink: 0,
                      }}
                    >
                      <Shield size={22} />
                    </div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontWeight: 600, fontSize: '0.96rem', color: 'var(--text-primary)' }}>
                          Connect via Account Aggregator
                        </span>
                        <span
                          style={{
                            fontSize: '0.66rem',
                            fontWeight: 700,
                            letterSpacing: '0.04em',
                            padding: '2px 6px',
                            borderRadius: 4,
                            background: 'rgba(234, 179, 8, 0.16)',
                            border: '1px solid rgba(234, 179, 8, 0.35)',
                            color: '#eab308',
                          }}
                        >
                          SANDBOX
                        </span>
                      </div>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-muted, #94a3b8)', marginTop: 4, maxWidth: 360, lineHeight: 1.4 }}>
                        Connect banks, investments, mutual funds and other supported accounts using consent-based account sharing.
                      </div>
                      <div style={{ fontSize: '0.75rem', marginTop: 4, fontWeight: 500, color: isAAConnected ? '#22c55e' : '#38bdf8' }}>
                        Status: {isAAConnected ? 'Sandbox Connected' : 'Sandbox Available'}
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setShowAAModal(true)}
                    style={{
                      padding: '8px 18px',
                      fontSize: '0.85rem',
                      fontWeight: 600,
                      flexShrink: 0,
                      background: '#0284c7',
                      borderColor: '#0284c7',
                    }}
                  >
                    {isAAConnected ? 'Manage' : 'Connect'}
                  </button>
                </div>

                {/* Platform Catalog List */}
                <div className="catalog-list" style={{ maxHeight: 380, overflowY: 'auto' }}>
                  {isLoading ? (
                    <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
                      <span>Loading platform catalog...</span>
                    </div>
                  ) : error ? (
                    <div style={{ padding: '24px', textAlign: 'center', color: '#ef4444' }}>
                      <p style={{ margin: '0 0 12px 0' }}>{error}</p>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={fetchCatalog}
                        style={{ fontSize: '0.82rem', padding: '6px 16px' }}
                      >
                        Retry
                      </button>
                    </div>
                  ) : filteredCatalog.length === 0 ? (
                    <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
                      <span>No platforms match your search.</span>
                    </div>
                  ) : (
                    filteredCatalog.map((platform) => {
                      const isAlreadyConnected =
                        connectedPlatformIds.includes(platform.id) ||
                        connectedPlatformIds.includes(platform.slug);

                      return (
                        <div
                          key={platform.id}
                          className="catalog-item"
                          onClick={() => handleSelectPlatform(platform)}
                          style={{ cursor: 'pointer' }}
                        >
                          <div className="catalog-item-left">
                            <PlatformLogo platform={platform} size={38} />
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <span className="catalog-item-name">{platform.name}</span>
                                {isAlreadyConnected && (
                                  <span
                                    style={{
                                      fontSize: '0.72rem',
                                      padding: '1px 6px',
                                      borderRadius: 4,
                                      background: 'var(--positive-bg, rgba(16, 185, 129, 0.08))',
                                      color: 'var(--positive, #059669)',
                                      fontWeight: 500
                                    }}
                                  >
                                    Connected
                                  </span>
                                )}
                              </div>
                              <div className="catalog-item-type">
                                {platform.category.replace(/_/g, ' ').toLowerCase()}
                                {platform.description && ` • ${platform.description.slice(0, 46)}...`}
                              </div>
                            </div>
                          </div>

                          <div className="catalog-item-actions" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSelectPlatform(platform);
                              }}
                              className="btn-secondary"
                              style={{
                                padding: '5px 10px',
                                fontSize: '0.78rem',
                                borderRadius: 6,
                              }}
                            >
                              Choose method →
                            </button>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </>
            ) : (
              /* STEP 2: CONNECTION METHODS FOR SELECTED PLATFORM */
              <div className="platform-connector-methods">
                {/* Platform Summary Card */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 14,
                    padding: '14px 16px',
                    borderRadius: 8,
                    background: 'var(--bg-subtle, #f1f5f9)',
                    border: '1px solid var(--border-subtle, #e2e8f0)',
                    marginBottom: 20
                  }}
                >
                  <PlatformLogo platform={selectedPlatform} size={44} />
                  <div>
                    <div style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {selectedPlatform.name}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {selectedPlatform.category.replace(/_/g, ' ').toLowerCase()}
                      {selectedPlatform.description && ` • ${selectedPlatform.description}`}
                    </div>
                  </div>
                </div>

                <div style={{ fontSize: '0.76rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)', marginBottom: 12 }}>
                  AVAILABLE CONNECTION METHODS
                </div>

                {isLoadingConnectors ? (
                  <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
                    <span>Checking supported connection methods...</span>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {connectors.map((c) => {
                      const isSandbox = c.status === 'SANDBOX' || c.connector_key === 'setu_aa' || c.connector_type === 'ACCOUNT_AGGREGATOR';
                      const isAvailable = c.status === 'AVAILABLE' || isSandbox;
                      const isComingSoon = !isAvailable && (c.status === 'COMING_SOON' || c.status === 'PLANNED');
                      const isNotified = notifiedConnectors[c.connector_key];

                      return (
                        <div
                          key={c.connector_key}
                          style={{
                            padding: '16px',
                            borderRadius: 8,
                            border: `1px solid ${isAvailable ? 'var(--border-focus, #cbd5e1)' : 'var(--border-subtle, #e2e8f0)'}`,
                            background: isAvailable ? 'var(--bg-surface, #ffffff)' : 'var(--bg-subtle, #f8fafc)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 10
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <span style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                                  {c.name || c.connector_type.replace(/_/g, ' ')}
                                </span>
                                <span
                                  style={{
                                    fontSize: '0.7rem',
                                    fontWeight: 600,
                                    padding: '2px 8px',
                                    borderRadius: 12,
                                    textTransform: 'uppercase',
                                    background: isSandbox
                                      ? 'rgba(234, 179, 8, 0.14)'
                                      : isAvailable
                                      ? 'var(--positive-bg, rgba(16, 185, 129, 0.08))'
                                      : 'var(--bg-subtle, #f1f5f9)',
                                    color: isSandbox
                                      ? '#eab308'
                                      : isAvailable
                                      ? 'var(--positive, #059669)'
                                      : 'var(--text-muted, #94a3b8)',
                                    border: `1px solid ${
                                      isSandbox
                                        ? 'rgba(234, 179, 8, 0.3)'
                                        : isAvailable
                                        ? 'rgba(16, 185, 129, 0.2)'
                                        : 'var(--border-subtle, #e2e8f0)'
                                    }`
                                  }}
                                >
                                  {isSandbox ? 'Sandbox Available' : isAvailable ? 'Available' : 'Coming Soon'}
                                </span>
                              </div>
                              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                                {c.requirements || (isSandbox ? 'Consent-based sharing (Setu sandbox)' : isAvailable ? 'No credentials required' : 'API connection')}
                              </div>
                            </div>

                            {/* Action Buttons */}
                            <div>
                              {isAvailable ? (
                                isSandbox || c.connector_type === 'ACCOUNT_AGGREGATOR' ? (
                                  <button
                                    type="button"
                                    onClick={() => setShowAAModal(true)}
                                    className="btn-primary"
                                    style={{
                                      padding: '7px 16px',
                                      fontSize: '0.82rem',
                                      borderRadius: 6,
                                      background: '#0284c7',
                                      color: '#ffffff',
                                      border: 'none',
                                      cursor: 'pointer',
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: 6
                                    }}
                                  >
                                    <Shield size={14} />
                                    <span>Connect Sandbox</span>
                                  </button>
                                ) : c.connector_type === 'IMPORT' ? (
                                  <button
                                    type="button"
                                    onClick={() => setImportPlatform(selectedPlatform)}
                                    className="btn-primary"
                                    style={{
                                      padding: '7px 16px',
                                      fontSize: '0.82rem',
                                      borderRadius: 6,
                                      background: 'var(--accent, #0f172a)',
                                      color: '#ffffff',
                                      border: 'none',
                                      cursor: 'pointer',
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: 6
                                    }}
                                  >
                                    <UploadCloud size={14} />
                                    <span>Import Statement</span>
                                  </button>
                                ) : c.connector_type === 'DIRECT_API' ? (
                                  <button
                                    type="button"
                                    onClick={() => setGrowwPlatform(selectedPlatform)}
                                    className="btn-primary"
                                    style={{
                                      padding: '7px 16px',
                                      fontSize: '0.82rem',
                                      borderRadius: 6,
                                      background: 'var(--positive, #059669)',
                                      color: '#ffffff',
                                      border: 'none',
                                      cursor: 'pointer',
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: 6
                                    }}
                                  >
                                    <Shield size={14} />
                                    <span>Connect Live API</span>
                                  </button>
                                ) : (
                                  <button
                                    type="button"
                                    onClick={() => handleManualEntry(selectedPlatform)}
                                    className="btn-primary"
                                    style={{
                                      padding: '7px 16px',
                                      fontSize: '0.82rem',
                                      borderRadius: 6,
                                      background: 'var(--accent, #0f172a)',
                                      color: '#ffffff',
                                      border: 'none',
                                      cursor: 'pointer',
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: 6
                                    }}
                                  >
                                    <PlusCircle size={14} />
                                    <span>Add Manually</span>
                                  </button>
                                )
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => handleNotifyMe(c.connector_key)}
                                  disabled={isNotified}
                                  className="btn-secondary"
                                  style={{
                                    padding: '6px 12px',
                                    fontSize: '0.78rem',
                                    borderRadius: 6,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 6,
                                    cursor: isNotified ? 'default' : 'pointer',
                                    opacity: isNotified ? 0.7 : 1
                                  }}
                                >
                                  {isNotified ? <Check size={13} color="var(--positive)" /> : <Bell size={13} />}
                                  <span>{isNotified ? 'Notification set' : 'Notify me'}</span>
                                </button>
                              )}
                            </div>
                          </div>

                          {/* Capabilities Pills */}
                          {c.capabilities && c.capabilities.length > 0 && (
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                              {c.capabilities.map((cap) => (
                                <span
                                  key={cap}
                                  style={{
                                    fontSize: '0.7rem',
                                    padding: '2px 7px',
                                    borderRadius: 4,
                                    background: 'var(--bg-subtle, #f1f5f9)',
                                    color: 'var(--text-muted, #64748b)',
                                    border: '1px solid var(--border-subtle, #e2e8f0)'
                                  }}
                                >
                                  {cap.toLowerCase()}
                                </span>
                              ))}
                            </div>
                          )}

                          {isComingSoon && (
                            <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                              <span>You can track {selectedPlatform.name} right now by</span>
                              <button
                                type="button"
                                onClick={() => handleManualEntry(selectedPlatform)}
                                style={{ background: 'none', border: 'none', color: 'var(--accent)', textDecoration: 'underline', cursor: 'pointer', padding: 0, fontSize: 'inherit' }}
                              >
                                adding your assets manually →
                              </button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Zero-Fabrication Security Guarantee */}
            <div style={{ marginTop: 20, paddingTop: 14, borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: 1.45 }}>
              <Shield size={16} style={{ flexShrink: 0, color: 'var(--positive, #059669)', marginTop: 2 }} />
              <div>
                <strong>Zero-Fabrication Guarantee:</strong> WealthHub never connects fake APIs or simulates accounts. We never ask for or store broker/bank passwords, PINs, or OTPs. All calculations come strictly from verified financial records.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Manual Asset/Account Entry Modal */}
      {manualPlatform && (
        <ManualAssetModal
          isOpen={Boolean(manualPlatform)}
          onClose={() => setManualPlatform(null)}
          platform={manualPlatform}
          onAssetAdded={() => {
            if (onPlatformAdded) onPlatformAdded();
            handleClose();
          }}
        />
      )}

      {/* Statement Import Modal */}
      {importPlatform && (
        <StatementImportModal
          isOpen={Boolean(importPlatform)}
          onClose={() => setImportPlatform(null)}
          targetPlatform={importPlatform}
          onImportComplete={() => {
            if (onPlatformAdded) onPlatformAdded();
            handleClose();
          }}
        />
      )}

      {/* Groww Live API Connection Modal */}
      {growwPlatform && (
        <GrowwConnectModal
          isOpen={Boolean(growwPlatform)}
          onClose={() => setGrowwPlatform(null)}
          platform={growwPlatform}
          onSuccess={() => {
            if (onPlatformAdded) onPlatformAdded();
            handleClose();
          }}
        />
      )}

      {/* Account Aggregator Sandbox Modal */}
      {showAAModal && (
        <AccountAggregatorConnectModal
          isOpen={showAAModal}
          onClose={() => setShowAAModal(false)}
          onSuccess={() => {
            if (onPlatformAdded) onPlatformAdded();
            handleClose();
          }}
        />
      )}
    </>
  );
}
