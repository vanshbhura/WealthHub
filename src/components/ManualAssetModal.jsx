import React, { useState } from 'react';
import { X, Check, AlertCircle } from 'lucide-react';
import { assetsApi } from '../api/assets';
import { api } from '../api/client';
import PlatformLogo from './PlatformLogo';

const ASSET_TYPES = [
  { value: 'STOCK', label: 'Stock / Equity' },
  { value: 'MUTUAL_FUND', label: 'Mutual Fund' },
  { value: 'ETF', label: 'Exchange Traded Fund (ETF)' },
  { value: 'FD', label: 'Fixed Deposit' },
  { value: 'RD', label: 'Recurring Deposit' },
  { value: 'P2P', label: 'P2P Loan' },
  { value: 'DIGITAL_GOLD', label: 'Digital Gold' },
  { value: 'DIGITAL_SILVER', label: 'Digital Silver' },
  { value: 'CRYPTO', label: 'Cryptocurrency' },
  { value: 'BOND', label: 'Bond / Debenture' },
  { value: 'SGB', label: 'Sovereign Gold Bond' },
  { value: 'EPF', label: 'EPF' },
  { value: 'PPF', label: 'PPF' },
  { value: 'NPS', label: 'NPS' },
  { value: 'REAL_ESTATE', label: 'Real Estate' },
  { value: 'CASH', label: 'Cash / Bank Savings' },
  { value: 'OTHER', label: 'Other Asset' },
];

export default function ManualAssetModal({
  isOpen,
  onClose,
  platform,
  onSuccess
}) {
  const [entryMode, setEntryMode] = useState('asset'); // 'asset' | 'account'
  const [name, setName] = useState('');
  const [assetType, setAssetType] = useState('STOCK');
  const [accountType, setAccountType] = useState('SAVINGS');
  const [quantity, setQuantity] = useState('1');
  const [buyPrice, setBuyPrice] = useState('');
  const [currentPrice, setCurrentPrice] = useState('');
  const [balance, setBalance] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen || !platform) return null;

  const isBank = platform.category === 'BANK';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (entryMode === 'account') {
        const val = parseFloat(balance) || 0;
        await api.post('/api/accounts', {
          platform_id: platform.id,
          account_name: name.trim() || `${platform.name} Account`,
          account_type: accountType,
          current_value: val,
          invested_value: val,
          currency: 'INR'
        });
      } else {
        const qty = parseFloat(quantity) || 1;
        const bp = parseFloat(buyPrice) || 0;
        const cp = parseFloat(currentPrice) || bp;
        const invested = bp * qty;
        const current = cp * qty;

        await assetsApi.createAsset({
          platform_id: platform.id,
          asset_type: assetType,
          name: name.trim(),
          quantity: qty,
          average_buy_price: bp,
          invested_amount: invested,
          current_price: cp,
          current_value: current,
          currency: 'INR',
          data_source: 'MANUAL'
        });
      }

      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      console.error('Error creating manual asset/account:', err);
      setError(err?.message || 'Failed to save. Please verify your inputs.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        style={{ maxWidth: 500 }}
      >
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <PlatformLogo platform={platform} size={32} />
            <div>
              <h2 className="modal-title" style={{ fontSize: '1.15rem' }}>
                Add to {platform.name}
              </h2>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Manual portfolio entry
              </div>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          {error && (
            <div style={{ padding: '10px 14px', borderRadius: 6, background: 'rgba(239, 68, 68, 0.08)', color: '#ef4444', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: 8 }}>
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          {/* Mode Selector */}
          <div style={{ display: 'flex', gap: 8, padding: 3, background: 'var(--bg-subtle, #f1f5f9)', borderRadius: 6 }}>
            <button
              type="button"
              onClick={() => setEntryMode('asset')}
              style={{
                flex: 1,
                padding: '6px 12px',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: entryMode === 'asset' ? 600 : 400,
                background: entryMode === 'asset' ? 'var(--bg-surface, #ffffff)' : 'transparent',
                color: 'var(--text-primary)',
                boxShadow: entryMode === 'asset' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none'
              }}
            >
              Individual Asset / Holding
            </button>
            <button
              type="button"
              onClick={() => setEntryMode('account')}
              style={{
                flex: 1,
                padding: '6px 12px',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: entryMode === 'account' ? 600 : 400,
                background: entryMode === 'account' ? 'var(--bg-surface, #ffffff)' : 'transparent',
                color: 'var(--text-primary)',
                boxShadow: entryMode === 'account' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none'
              }}
            >
              Account Balance (Savings/FD)
            </button>
          </div>

          {entryMode === 'asset' ? (
            <>
              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: 6 }}>
                  Asset Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Reliance Industries, Nifty 50 Index Fund"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', paddingLeft: 12 }}
                />
              </div>

              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: 6 }}>
                  Asset Category
                </label>
                <select
                  value={assetType}
                  onChange={(e) => setAssetType(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', paddingLeft: 12 }}
                >
                  {ASSET_TYPES.map(t => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
                <div>
                  <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: 6 }}>
                    Quantity
                  </label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    className="search-input"
                    style={{ width: '100%', paddingLeft: 12 }}
                  />
                </div>
                <div>
                  <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: 6 }}>
                    Buy Price (₹)
                  </label>
                  <input
                    type="number"
                    step="any"
                    required
                    placeholder="0"
                    value={buyPrice}
                    onChange={(e) => setBuyPrice(e.target.value)}
                    className="search-input"
                    style={{ width: '100%', paddingLeft: 12 }}
                  />
                </div>
                <div>
                  <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: 6 }}>
                    Current Price (₹)
                  </label>
                  <input
                    type="number"
                    step="any"
                    required
                    placeholder="0"
                    value={currentPrice}
                    onChange={(e) => setCurrentPrice(e.target.value)}
                    className="search-input"
                    style={{ width: '100%', paddingLeft: 12 }}
                  />
                </div>
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: 6 }}>
                  Account Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder={`e.g. ${platform.name} Primary Savings`}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', paddingLeft: 12 }}
                />
              </div>

              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: 6 }}>
                  Account Type
                </label>
                <select
                  value={accountType}
                  onChange={(e) => setAccountType(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', paddingLeft: 12 }}
                >
                  <option value="SAVINGS">Savings Account</option>
                  <option value="CURRENT">Current Account</option>
                  <option value="TERM_DEPOSIT">Fixed / Term Deposit</option>
                  <option value="DEMAT">Trading / Demat Wallet</option>
                  <option value="P2P_WALLET">P2P Lending Wallet</option>
                </select>
              </div>

              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: 6 }}>
                  Current Balance / Value (₹) *
                </label>
                <input
                  type="number"
                  step="any"
                  required
                  placeholder="e.g. 50000"
                  value={balance}
                  onChange={(e) => setBalance(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', paddingLeft: 12 }}
                />
              </div>
            </>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
              style={{
                padding: '8px 16px',
                borderRadius: 6,
                border: '1px solid var(--border-subtle, #e2e8f0)',
                background: 'transparent',
                color: 'var(--text-secondary)',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                padding: '8px 18px',
                borderRadius: 6,
                border: 'none',
                background: 'var(--accent, #0f172a)',
                color: '#ffffff',
                fontWeight: 500,
                cursor: 'pointer',
                opacity: isSubmitting ? 0.7 : 1
              }}
            >
              {isSubmitting ? 'Saving...' : 'Save to WealthHub'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
